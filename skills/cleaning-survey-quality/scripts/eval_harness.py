#!/usr/bin/env python3
"""
Fixed evaluation harness for survey quality ML experiments.
DO NOT MODIFY. This is the ground truth metric.

Evaluates a trained model on per-dataset test splits and reports F1.
The metric is average F1 across all 11 datasets.

Usage: python3 eval_harness.py <train_script.py>
  - Imports the train_script, calls its train_and_predict function
  - train_and_predict(train_df, val_df, test_df) -> (y_pred, y_proba)
  - Reports per-dataset and aggregate F1, precision, recall, accuracy
"""
from __future__ import annotations

import importlib
import json
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import (
    accuracy_score, f1_score, precision_score, recall_score, roc_auc_score,
)

warnings.filterwarnings("ignore")

sys.path.insert(0, str(Path(__file__).parent))
from survey_quality_ml import (
    ANNOTATED_DIR, DATASET_MAP, load_signal_map,
    extract_features_from_excel, add_supplier_risk, prepare_features,
)
from per_dataset_eval import split_dataset

# Fixed constants
SPLIT_RATIOS = (0.70, 0.15, 0.15)
RANDOM_STATE = 42
TARGET_F1 = 0.90


def run_evaluation(train_script_path: str):
    """Run evaluation using the train script's train_and_predict function."""
    # Import the train script
    spec = importlib.util.spec_from_file_location("train_script", train_script_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, "train_and_predict"):
        print(f"ERROR: {train_script_path} must define train_and_predict(train_df, val_df, test_df)")
        return None

    signal_map = load_signal_map()

    # Extract features from all datasets
    all_dfs = {}
    for fname in sorted(DATASET_MAP.keys()):
        fp = ANNOTATED_DIR / fname
        if not fp.exists():
            continue
        df, _ = extract_features_from_excel(fp, signal_map)
        if df is not None and len(df) > 0:
            all_dfs[fname] = df

    results = []
    for fname in sorted(all_dfs.keys()):
        df = all_dfs[fname]
        if len(df) < 50 or df["label"].nunique() < 2:
            continue

        train_df, val_df, test_df = split_dataset(df, random_state=RANDOM_STATE)

        # Add supplier risk from train only
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

        # Call the train script's function
        y_test = test_df["label"].values
        y_pred, y_proba = module.train_and_predict(train_df, val_df, test_df)

        # Metrics
        acc = accuracy_score(y_test, y_pred)
        prec = precision_score(y_test, y_pred, zero_division=0)
        rec = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        auc = roc_auc_score(y_test, y_proba) if len(set(y_test)) > 1 else 0

        n = len(y_test)
        n_rej = int(y_test.sum())
        keep_all_acc = 1 - n_rej / n

        results.append({
            "dataset": fname,
            "n": n,
            "n_rej": n_rej,
            "reject_rate": n_rej / n,
            "accuracy": float(acc),
            "keep_all_accuracy": float(keep_all_acc),
            "precision": float(prec),
            "recall": float(rec),
            "f1": float(f1),
            "auc": float(auc),
            "beats_baseline": acc > keep_all_acc,
        })

    # Aggregate
    n_total = sum(r["n"] for r in results)
    avg_f1 = np.mean([r["f1"] for r in results])
    avg_acc = np.mean([r["accuracy"] for r in results])
    avg_prec = np.mean([r["precision"] for r in results])
    avg_rec = np.mean([r["recall"] for r in results])
    n_beat = sum(1 for r in results if r["beats_baseline"])

    print(f"\n{'='*120}")
    print(f"EVALUATION RESULTS — {train_script_path}")
    print(f"{'='*120}")
    print(f"\n{'Dataset':<45} {'N':>5} {'Rej':>5} {'Rate':>6} {'Acc':>6} {'Base':>6} {'Beat':>5} {'Prec':>6} {'Rec':>6} {'F1':>6} {'AUC':>6}")
    print(f"{'-'*45} {'-'*5} {'-'*5} {'-'*6} {'-'*6} {'-'*6} {'-'*5} {'-'*6} {'-'*6} {'-'*6} {'-'*6}")
    for r in results:
        beat = "Y" if r["beats_baseline"] else "N"
        print(f"{r['dataset']:<45} {r['n']:>5} {r['n_rej']:>5} {r['reject_rate']:>6.1%} {r['accuracy']:>6.1%} {r['keep_all_accuracy']:>6.1%} {beat:>5} {r['precision']:>6.1%} {r['recall']:>6.1%} {r['f1']:>6.1%} {r['auc']:>6.3f}")

    print(f"\n{'AGGREGATE':<45} {'':>5} {'':>5} {'':>6} {avg_acc:>6.1%} {'':>6} {n_beat:>5}/{len(results)} {avg_prec:>6.1%} {avg_rec:>6.1%} {avg_f1:>6.1%}")
    print(f"\n  Average F1:    {avg_f1:.1%}  (target: {TARGET_F1:.0%})")
    print(f"  Average Acc:   {avg_acc:.1%}")
    print(f"  Beat baseline: {n_beat}/{len(results)} datasets")

    if avg_f1 >= TARGET_F1:
        print(f"\n  *** TARGET REACHED: {avg_f1:.1%} >= {TARGET_F1:.0%} ***")
    else:
        gap = TARGET_F1 - avg_f1
        print(f"\n  Gap to target: {gap:.1%}")

    return {"avg_f1": float(avg_f1), "avg_acc": float(avg_acc), "results": results}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 eval_harness.py <train_script.py>")
        sys.exit(1)
    results = run_evaluation(sys.argv[1])
    if results:
        # Output machine-readable summary
        print(f"\n---\navg_f1: {results['avg_f1']:.6f}")
