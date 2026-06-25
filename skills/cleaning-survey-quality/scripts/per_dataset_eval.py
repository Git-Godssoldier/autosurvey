#!/usr/bin/env python3
"""Per-dataset train/test/val evaluation with full skill flow.

For each of the 11 annotated datasets:
1. Split into 70% train, 15% val, 15% test (stratified by label)
2. Train a Gradient Boosting model on the train split
3. Tune threshold on validation split to maximize accuracy
4. Run full skill flow (ML + agent rules + semantic parsing) on test split
5. Report accuracy, precision, recall, F1

Usage:
    python3 per_dataset_eval.py
    python3 per_dataset_eval.py --dataset "260111_Delta Water Filtration.xlsx"
    python3 per_dataset_eval.py --report  # also generate the plain writing report
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
from predict_quality import apply_agent_rules, extract_features as extract_features_predict


def split_dataset(df, train_size=0.70, val_size=0.15, test_size=0.15, random_state=42):
    """Split a dataset into train, validation, and test sets, stratified by label."""
    y = df["label"]
    sss1 = StratifiedShuffleSplit(n_splits=1, test_size=val_size + test_size, random_state=random_state)
    train_idx, temp_idx = next(sss1.split(df, y))
    train_df = df.iloc[train_idx].copy()
    temp_df = df.iloc[temp_idx].copy()

    temp_ratio = test_size / (val_size + test_size)
    sss2 = StratifiedShuffleSplit(n_splits=1, test_size=temp_ratio, random_state=random_state)
    val_idx_new, test_idx_new = next(sss2.split(temp_df, temp_df["label"]))
    val_df = temp_df.iloc[val_idx_new].copy()
    test_df = temp_df.iloc[test_idx_new].copy()

    return train_df, val_df, test_df


def train_and_evaluate_dataset(fname, df, signal_map):
    """Train on train split, tune on val, evaluate on test for a single dataset."""
    if len(df) < 50 or df["label"].nunique() < 2:
        return None

    train_df, val_df, test_df = split_dataset(df)

    # Add supplier risk from train to val and test
    train_df, val_df = add_supplier_risk(train_df, val_df)
    # test_df needs supplier risk from the same train_df
    # But train_df already has supplier_reject_rate from the first call
    # So we just map it directly
    global_rate = float(train_df["label"].mean())
    sr = train_df.groupby("supplier_name")["supplier_reject_rate"].first().reset_index()
    sr.columns = ["supplier_name", "supplier_reject_rate"]
    # Remove existing if present, then merge
    if "supplier_reject_rate" in test_df.columns:
        test_df = test_df.drop(columns=["supplier_reject_rate"])
    test_df = test_df.merge(sr, on="supplier_name", how="left")
    test_df["supplier_reject_rate"] = test_df["supplier_reject_rate"].fillna(global_rate)
    for df in [test_df]:
        df["supplier_x_signals"] = df["supplier_reject_rate"] * df["signal_count"]
        df["supplier_x_t1"] = df["supplier_reject_rate"] * df["t1_count"]
        df["supplier_x_t2"] = df["supplier_reject_rate"] * df["t2_count"]
        df["signals_x_matrix"] = df["signal_count"] * (1 - df["matrix_unique_ratio"])

    X_train, y_train = prepare_features(train_df)
    X_val, y_val = prepare_features(val_df)
    X_test, y_test = prepare_features(test_df)

    # Align columns
    for c in X_train.columns:
        if c not in X_val.columns: X_val[c] = 0
        if c not in X_test.columns: X_test[c] = 0
    for c in X_val.columns:
        if c not in X_train.columns: X_train[c] = 0
    for c in X_test.columns:
        if c not in X_train.columns: X_train[c] = 0
    X_val = X_val[X_train.columns]
    X_test = X_test[X_train.columns]

    # Class weights
    n_pos = max((y_train == 1).sum(), 1)
    n_neg = max((y_train == 0).sum(), 1)
    w = np.where(y_train == 1, len(y_train) / (2 * n_pos), len(y_train) / (2 * n_neg))

    # Train
    model = GradientBoostingClassifier(
        n_estimators=300, max_depth=4, learning_rate=0.05,
        subsample=0.8, random_state=42, min_samples_leaf=10
    )
    model.fit(X_train, y_train, sample_weight=w)

    # Calibrate on train
    y_train_proba = model.predict_proba(X_train)[:, 1]
    iso = IsotonicRegression(out_of_bounds='clip')
    iso.fit(y_train_proba, y_train)

    # Tune threshold on validation
    y_val_cal = iso.transform(model.predict_proba(X_val)[:, 1])
    best_acc, best_t = 0, 0.5
    for t in np.linspace(0.01, 0.99, 200):
        pred = (y_val_cal >= t).astype(int)
        acc = accuracy_score(y_val, pred)
        if acc > best_acc:
            best_acc = acc
            best_t = t

    # Evaluate on test
    y_test_proba = model.predict_proba(X_test)[:, 1]
    y_test_cal = iso.transform(y_test_proba)
    y_test_pred = (y_test_cal >= best_t).astype(int)

    # Also run agent rules on test
    rule_dets = apply_agent_rules(test_df, {}, {})
    rule_pred = (rule_dets["rule_determination"] == "DISCARD").astype(int)

    # Combined: ML OR rules
    combined_pred = np.maximum(y_test_pred, rule_pred)

    # Metrics
    acc_ml = accuracy_score(y_test, y_test_pred)
    acc_rules = accuracy_score(y_test, rule_pred)
    acc_combined = accuracy_score(y_test, combined_pred)

    prec_ml = precision_score(y_test, y_test_pred, zero_division=0)
    rec_ml = recall_score(y_test, y_test_pred, zero_division=0)
    f1_ml = f1_score(y_test, y_test_pred, zero_division=0)
    auc = roc_auc_score(y_test, y_test_proba) if y_test.nunique() > 1 else 0

    prec_comb = precision_score(y_test, combined_pred, zero_division=0)
    rec_comb = recall_score(y_test, combined_pred, zero_division=0)
    f1_comb = f1_score(y_test, combined_pred, zero_division=0)

    cm = confusion_matrix(y_test, y_test_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()
    cm_comb = confusion_matrix(y_test, combined_pred, labels=[0, 1])
    tn_c, fp_c, fn_c, tp_c = cm_comb.ravel()

    # Feature importance
    feat_imp = sorted(zip(X_train.columns, model.feature_importances_), key=lambda x: -x[1])[:10]

    result = {
        "dataset": fname,
        "n_total": len(df),
        "n_train": len(train_df),
        "n_val": len(val_df),
        "n_test": len(test_df),
        "n_test_rejected": int(y_test.sum()),
        "test_reject_rate": float(y_test.mean()),
        "threshold": float(best_t),
        "auc": float(auc),
        "ml": {
            "accuracy": float(acc_ml),
            "precision": float(prec_ml),
            "recall": float(rec_ml),
            "f1": float(f1_ml),
            "tp": int(tp), "fp": int(fp), "tn": int(tn), "fn": int(fn),
        },
        "rules": {
            "accuracy": float(acc_rules),
        },
        "combined": {
            "accuracy": float(acc_combined),
            "precision": float(prec_comb),
            "recall": float(rec_comb),
            "f1": float(f1_comb),
            "tp": int(tp_c), "fp": int(fp_c), "tn": int(tn_c), "fn": int(fn_c),
        },
        "top_features": [{"feature": f, "importance": float(i)} for f, i in feat_imp],
    }

    return result


def run_all_datasets():
    """Run evaluation on all 11 datasets."""
    print("Loading signal map...")
    signal_map = load_signal_map()

    print("\nExtracting features from all annotated datasets...")
    all_dfs = {}
    for fname in sorted(DATASET_MAP.keys()):
        fp = ANNOTATED_DIR / fname
        if not fp.exists():
            continue
        df, _ = extract_features_from_excel(fp, signal_map)
        if df is not None and len(df) > 0:
            all_dfs[fname] = df
            n_rej = (df["label"] == 1).sum()
            print(f"  {fname}: {len(df)} respondents, {n_rej} rejected ({n_rej/len(df):.1%})")

    print(f"\n{'='*120}")
    print("PER-DATASET TRAIN/VAL/TEST EVALUATION (70/15/15 split, stratified)")
    print(f"{'='*120}")

    all_results = []
    for fname in sorted(all_dfs.keys()):
        df = all_dfs[fname]
        result = train_and_evaluate_dataset(fname, df, signal_map)
        if result:
            all_results.append(result)
            r = result
            print(f"\n{fname}")
            print(f"  Split: train={r['n_train']}, val={r['n_val']}, test={r['n_test']} (rejected={r['n_test_rejected']})")
            print(f"  Threshold: {r['threshold']:.3f}, AUC: {r['auc']:.3f}")
            print(f"  ML:       Acc={r['ml']['accuracy']:.1%}  Prec={r['ml']['precision']:.1%}  Rec={r['ml']['recall']:.1%}  F1={r['ml']['f1']:.1%}")
            print(f"  Rules:    Acc={r['rules']['accuracy']:.1%}")
            print(f"  Combined: Acc={r['combined']['accuracy']:.1%}  Prec={r['combined']['precision']:.1%}  Rec={r['combined']['recall']:.1%}  F1={r['combined']['f1']:.1%}")
            print(f"  ML CM:    TP={r['ml']['tp']}  FP={r['ml']['fp']}  TN={r['ml']['tn']}  FN={r['ml']['fn']}")
            print(f"  Comb CM:  TP={r['combined']['tp']}  FP={r['combined']['fp']}  TN={r['combined']['tn']}  FN={r['combined']['fn']}")
            print(f"  Top features:")
            for f in r["top_features"][:5]:
                print(f"    {f['feature']}: {f['importance']:.4f}")

    # Aggregate
    print(f"\n{'='*120}")
    print("AGGREGATE")
    print(f"{'='*120}")
    n = sum(r["n_test"] for r in all_results)
    tp = sum(r["ml"]["tp"] for r in all_results)
    fp = sum(r["ml"]["fp"] for r in all_results)
    tn = sum(r["ml"]["tn"] for r in all_results)
    fn = sum(r["ml"]["fn"] for r in all_results)
    acc = (tp + tn) / n
    print(f"  ML aggregate: Acc={acc:.1%} (TP={tp}, FP={fp}, TN={tn}, FN={fn})")

    tp_c = sum(r["combined"]["tp"] for r in all_results)
    fp_c = sum(r["combined"]["fp"] for r in all_results)
    tn_c = sum(r["combined"]["tn"] for r in all_results)
    fn_c = sum(r["combined"]["fn"] for r in all_results)
    acc_c = (tp_c + tn_c) / n
    print(f"  Combined aggregate: Acc={acc_c:.1%} (TP={tp_c}, FP={fp_c}, TN={tn_c}, FN={fn_c})")

    # Per-dataset accuracy summary
    print(f"\n  Per-dataset ML accuracy:")
    for r in sorted(all_results, key=lambda x: -x["ml"]["accuracy"]):
        marker = " ***" if r["ml"]["accuracy"] >= 0.90 else ""
        print(f"    {r['dataset']}: {r['ml']['accuracy']:.1%}{marker}")

    print(f"\n  Per-dataset combined accuracy:")
    for r in sorted(all_results, key=lambda x: -x["combined"]["accuracy"]):
        marker = " ***" if r["combined"]["accuracy"] >= 0.90 else ""
        print(f"    {r['dataset']}: {r['combined']['accuracy']:.1%}{marker}")

    # Save results
    output_path = Path(__file__).parent.parent / "models" / "per_dataset_eval_results.json"
    with open(output_path, "w") as f:
        json.dump(all_results, f, indent=2)
    print(f"\n  Results saved to {output_path}")

    return all_results


def main():
    dataset_filter = None
    if "--dataset" in sys.argv:
        idx = sys.argv.index("--dataset")
        dataset_filter = sys.argv[idx + 1]

    if dataset_filter:
        signal_map = load_signal_map()
        fp = ANNOTATED_DIR / dataset_filter
        if not fp.exists():
            print(f"File not found: {fp}")
            return
        df, _ = extract_features_from_excel(fp, signal_map)
        result = train_and_evaluate_dataset(dataset_filter, df, signal_map)
        if result:
            print(json.dumps(result, indent=2))
    else:
        run_all_datasets()


if __name__ == "__main__":
    main()
