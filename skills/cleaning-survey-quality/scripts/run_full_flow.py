#!/usr/bin/env python3
"""Run the full skill flow on one dataset's test split as a worked example.

Trains on the train split, tunes on val, then runs the full pipeline on the test split:
1. ML model prediction (Gradient Boosting with 156 features)
2. Agent rules (TIER 1/2/3 signals, straightlining, duplicates, timing)
3. Semantic parsing (Datamap, field roles, answer chains)
4. Combined determination with per-respondent justification

Outputs a detailed report showing every test respondent with their prediction,
the signals that fired, and whether the prediction was correct.
"""
from __future__ import annotations

import json
import re
import sys
import warnings
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
    f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import StratifiedShuffleSplit

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent))
from survey_quality_ml import (
    ANNOTATED_DIR, DATASET_MAP, load_signal_map,
    extract_features_from_excel, add_supplier_risk, prepare_features,
    ALL_SIGNALS, T1_SIGNALS, T2_SIGNALS,
)
from predict_quality import apply_agent_rules
from per_dataset_eval import split_dataset


def run_full_flow_on_dataset(fname):
    """Run the full skill flow on one dataset and produce a detailed report."""
    signal_map = load_signal_map()
    fp = ANNOTATED_DIR / fname
    df, datamap = extract_features_from_excel(fp, signal_map)

    print(f"Dataset: {fname}")
    print(f"  Total: {len(df)} respondents")
    print(f"  Rejected: {(df['label']==1).sum()} ({(df['label']==1).mean():.1%})")

    # Split
    train_df, val_df, test_df = split_dataset(df)
    print(f"  Split: train={len(train_df)}, val={len(val_df)}, test={len(test_df)}")

    # Add supplier risk
    train_df, val_df = add_supplier_risk(train_df, val_df)
    global_rate = float(train_df["label"].mean())
    sr = train_df.groupby("supplier_name")["supplier_reject_rate"].first().reset_index()
    sr.columns = ["supplier_name", "supplier_reject_rate"]
    if "supplier_reject_rate" in test_df.columns:
        test_df = test_df.drop(columns=["supplier_reject_rate"])
    test_df = test_df.merge(sr, on="supplier_name", how="left")
    test_df["supplier_reject_rate"] = test_df["supplier_reject_rate"].fillna(global_rate)
    for d in [test_df]:
        d["supplier_x_signals"] = d["supplier_reject_rate"] * d["signal_count"]
        d["supplier_x_t1"] = d["supplier_reject_rate"] * d["t1_count"]
        d["supplier_x_t2"] = d["supplier_reject_rate"] * d["t2_count"]
        d["signals_x_matrix"] = d["signal_count"] * (1 - d["matrix_unique_ratio"])

    # Prepare features
    X_train, y_train = prepare_features(train_df)
    X_val, y_val = prepare_features(val_df)
    X_test, y_test = prepare_features(test_df)

    # Align
    for c in X_train.columns:
        if c not in X_val.columns: X_val[c] = 0
        if c not in X_test.columns: X_test[c] = 0
    for c in X_val.columns:
        if c not in X_train.columns: X_train[c] = 0
    for c in X_test.columns:
        if c not in X_train.columns: X_train[c] = 0
    X_val = X_val[X_train.columns]
    X_test = X_test[X_train.columns]

    # Train
    n_pos = max((y_train == 1).sum(), 1)
    n_neg = max((y_train == 0).sum(), 1)
    w = np.where(y_train == 1, len(y_train) / (2 * n_pos), len(y_train) / (2 * n_neg))

    model = GradientBoostingClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, random_state=42, min_samples_leaf=10
    )
    model.fit(X_train, y_train, sample_weight=w)

    # Calibrate
    y_train_proba = model.predict_proba(X_train)[:, 1]
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(y_train_proba, y_train)

    # Tune threshold on val
    y_val_cal = iso.transform(model.predict_proba(X_val)[:, 1])
    best_acc, best_t = 0, 0.5
    for t in np.linspace(0.01, 0.99, 200):
        pred = (y_val_cal >= t).astype(int)
        acc = accuracy_score(y_val, pred)
        if acc > best_acc:
            best_acc = acc
            best_t = t

    print(f"  Threshold: {best_t:.3f} (val accuracy: {best_acc:.1%})")

    # Predict on test
    y_test_proba = model.predict_proba(X_test)[:, 1]
    y_test_cal = iso.transform(y_test_proba)
    y_test_pred = (y_test_cal >= best_t).astype(int)

    # Agent rules
    rule_dets = apply_agent_rules(test_df, datamap, {})

    # Combined
    rule_pred = (rule_dets["rule_determination"] == "DISCARD").astype(int).values
    combined_pred = np.maximum(y_test_pred, rule_pred)

    # Metrics
    acc_ml = accuracy_score(y_test, y_test_pred)
    acc_comb = accuracy_score(y_test, combined_pred)
    prec_ml = precision_score(y_test, y_test_pred, zero_division=0)
    rec_ml = recall_score(y_test, y_test_pred, zero_division=0)
    f1_ml = f1_score(y_test, y_test_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_test_proba) if y_test.nunique() > 1 else 0

    cm = confusion_matrix(y_test, y_test_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    print(f"\n  ML Results:")
    print(f"    Accuracy:  {acc_ml:.1%}")
    print(f"    Precision: {prec_ml:.1%}")
    print(f"    Recall:    {rec_ml:.1%}")
    print(f"    F1:        {f1_ml:.1%}")
    print(f"    AUC:       {auc:.3f}")
    print(f"    TP={tp}  FP={fp}  TN={tn}  FN={fn}")

    # Feature importance
    feat_imp = sorted(zip(X_train.columns, model.feature_importances_), key=lambda x: -x[1])[:15]
    print(f"\n  Top features:")
    for f, i in feat_imp:
        print(f"    {f}: {i:.4f}")

    # Per-respondent details for the test split
    print(f"\n  Per-respondent details (test split, {len(test_df)} respondents):")
    print(f"  {'ID':<20} {'Label':<6} {'ML':<6} {'Rule':<6} {'Comb':<6} {'Score':<8} {'Reasons'}")
    print(f"  {'-'*20} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*8} {'-'*40}")

    correct = 0
    for i in range(len(test_df)):
        rid = test_df.iloc[i]["respondent_id"]
        label = int(y_test.iloc[i])
        ml_p = int(y_test_pred[i])
        rule_p = int(rule_pred[i])
        comb_p = int(combined_pred[i])
        score = float(y_test_cal[i])
        reasons = rule_dets.iloc[i]["rule_reasons"]
        reason_str = "; ".join(reasons[:3]) if reasons else ""

        is_correct = (comb_p == label)
        if is_correct:
            correct += 1

        # Only print errors and discards for brevity
        if not is_correct or comb_p == 1:
            mark = "OK" if is_correct else "WRONG"
            print(f"  {rid:<20} {label:<6} {ml_p:<6} {rule_p:<6} {comb_p:<6} {score:<8.3f} {reason_str[:40]}")

    print(f"\n  Combined accuracy: {acc_comb:.1%} ({correct}/{len(test_df)} correct)")

    # Save detailed results
    results = {
        "dataset": fname,
        "n_total": len(df),
        "n_train": len(train_df),
        "n_val": len(val_df),
        "n_test": len(test_df),
        "threshold": float(best_t),
        "auc": float(auc),
        "ml": {
            "accuracy": float(acc_ml),
            "precision": float(prec_ml),
            "recall": float(rec_ml),
            "f1": float(f1_ml),
            "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
        },
        "combined": {
            "accuracy": float(acc_comb),
        },
        "top_features": [{"feature": f, "importance": float(i)} for f, i in feat_imp],
    }

    output_path = Path(__file__).parent.parent / "models" / f"full_flow_{fname.replace('.xlsx', '.json')}"
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\n  Results saved to {output_path}")

    return results


if __name__ == "__main__":
    fname = sys.argv[1] if len(sys.argv) > 1 else "251205_TFG Contractor Index Q1.xlsx"
    run_full_flow_on_dataset(fname)
