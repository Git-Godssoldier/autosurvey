#!/usr/bin/env python3
"""Leakage audit: run per-dataset eval with and without signal map features.

Tests whether the signal map features are leaking label information by:
1. Running with all features (baseline)
2. Running without signal map features (sig_*, signal_count, t1/t2/t3_count)
3. Running without supplier features (supplier_reject_rate, supplier_x_*)
4. Running with ONLY raw data features (no signals, no supplier risk)

If accuracy drops significantly when removing signal map features, they may be leaking.
If accuracy drops when removing supplier features, the model relies on supplier risk.
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
    accuracy_score, f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.model_selection import StratifiedShuffleSplit

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent.parent))
from survey_quality_ml import (
    ANNOTATED_DIR, DATASET_MAP, load_signal_map,
    extract_features_from_excel, add_supplier_risk, prepare_features,
)
from per_dataset_eval import split_dataset


def run_eval_variant(df, train_df, val_df, test_df, feature_filter=None, label="baseline"):
    """Run evaluation with optional feature filtering."""
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

    X_train, y_train = prepare_features(train_df)
    X_val, y_val = prepare_features(val_df)
    X_test, y_test = prepare_features(test_df)

    # Apply feature filter
    if feature_filter:
        keep = [c for c in X_train.columns if feature_filter(c)]
        X_train = X_train[keep]
        X_val = X_val[[c for c in keep if c in X_val.columns] + [c for c in X_val.columns if c not in keep]]
        X_test = X_test[[c for c in keep if c in X_test.columns] + [c for c in X_test.columns if c not in keep]]
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

    # Tune threshold
    y_val_cal = iso.transform(model.predict_proba(X_val)[:, 1])
    best_acc, best_t = 0, 0.5
    for t in np.linspace(0.01, 0.99, 200):
        pred = (y_val_cal >= t).astype(int)
        acc = accuracy_score(y_val, pred)
        if acc > best_acc:
            best_acc = acc
            best_t = t

    # Evaluate
    y_test_proba = model.predict_proba(X_test)[:, 1]
    y_test_cal = iso.transform(y_test_proba)
    y_test_pred = (y_test_cal >= best_t).astype(int)

    acc = accuracy_score(y_test, y_test_pred)
    prec = precision_score(y_test, y_test_pred, zero_division=0)
    rec = recall_score(y_test, y_test_pred, zero_division=0)
    f1 = f1_score(y_test, y_test_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_test_proba) if y_test.nunique() > 1 else 0

    return {
        "label": label,
        "n_features": len(X_train.columns),
        "accuracy": float(acc),
        "precision": float(prec),
        "recall": float(rec),
        "f1": float(f1),
        "auc": float(auc),
        "threshold": float(best_t),
    }


def audit_dataset(fname, df):
    """Run all leakage audit variants for one dataset."""
    train_df, val_df, test_df = split_dataset(df)

    variants = [
        ("all features", None),
        ("no signal map", lambda c: not (c.startswith("sig_") or c in ("signal_count", "t1_count", "t2_count", "t3_count", "signal_count_zscore"))),
        ("no supplier risk", lambda c: not (c.startswith("supplier_") or c in ("supplier_x_signals", "supplier_x_t1", "supplier_x_t2"))),
        ("no signals + no supplier", lambda c: not (c.startswith("sig_") or c in ("signal_count", "t1_count", "t2_count", "t3_count", "signal_count_zscore") or c.startswith("supplier_") or c in ("supplier_x_signals", "supplier_x_t1", "supplier_x_t2"))),
        ("raw data only", lambda c: not (c.startswith("sig_") or c in ("signal_count", "t1_count", "t2_count", "t3_count", "signal_count_zscore") or c.startswith("supplier_") or c in ("supplier_x_signals", "supplier_x_t1", "supplier_x_t2", "signals_x_matrix"))),
    ]

    results = []
    for label, filter_fn in variants:
        # Fresh copies
        tr = train_df.copy()
        va = val_df.copy()
        te = test_df.copy()
        r = run_eval_variant(df, tr, va, te, filter_fn, label)
        results.append(r)

    return results


def main():
    signal_map = load_signal_map()

    # Focus on the datasets that hit 90%+
    target_datasets = [
        "251205_TFG Contractor Index Q1.xlsx",
        "251101_THD CX.xlsx",
        "260501_ODL.xlsx",
    ]

    all_dfs = {}
    for fname in sorted(DATASET_MAP.keys()):
        fp = ANNOTATED_DIR / fname
        if not fp.exists():
            continue
        df, _ = extract_features_from_excel(fp, signal_map)
        if df is not None and len(df) > 0:
            all_dfs[fname] = df

    print(f"{'='*120}")
    print("LEAKAGE AUDIT: Running each dataset with feature subsets")
    print(f"{'='*120}")

    for fname in target_datasets:
        if fname not in all_dfs:
            continue
        df = all_dfs[fname]
        n_rej = (df["label"] == 1).sum()
        print(f"\n{fname} ({len(df)} respondents, {n_rej} rejected, {n_rej/len(df):.1%})")
        print(f"  {'Variant':<30} {'N_feat':<8} {'Acc':<8} {'Prec':<8} {'Rec':<8} {'F1':<8} {'AUC':<8}")
        print(f"  {'-'*30} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8} {'-'*8}")

        results = audit_dataset(fname, df)
        for r in results:
            marker = " ***" if r["accuracy"] >= 0.90 else ""
            print(f"  {r['label']:<30} {r['n_features']:<8} {r['accuracy']:<8.1%} {r['precision']:<8.1%} {r['recall']:<8.1%} {r['f1']:<8.1%} {r['auc']:<8.3f}{marker}")

        # Check: does accuracy drop significantly without signal map?
        base = results[0]["accuracy"]
        no_sig = results[1]["accuracy"]
        no_sup = results[2]["accuracy"]
        raw = results[4]["accuracy"]
        print(f"\n  Accuracy drop without signals: {base - no_sig:+.1%}")
        print(f"  Accuracy drop without supplier: {base - no_sup:+.1%}")
        print(f"  Accuracy drop to raw data only: {base - raw:+.1%}")

        if no_sig < base - 0.05:
            print(f"  WARNING: Signal map features may be leaking (drop of {base - no_sig:.1%})")
        if no_sup < base - 0.05:
            print(f"  NOTE: Model relies heavily on supplier risk (drop of {base - no_sup:.1%})")

    # Save full results
    output = {}
    for fname in target_datasets:
        if fname in all_dfs:
            output[fname] = audit_dataset(fname, all_dfs[fname])

    output_path = Path(__file__).parent.parent.parent / "models" / "leakage_audit_results.json"
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    main()
