#!/usr/bin/env python3
"""Compare v2 (with client signals) vs v1 (without) vs client ground truth for Delta."""

import json
import csv
from collections import Counter, defaultdict
from pathlib import Path

SIGNAL_MAP = "/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/status-ground-truth-calibration/core_loop_2026-06-24/status_respondent_signal_map.csv"
V1_DIR = Path("/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/blind-runs-agent/106-2502 Delta Water Filtration")
V2_DIR = Path("/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/blind-runs-agent-v2/106-2502 Delta Water Filtration")
DATASET = "260111_Delta Water Filtration.xlsx"


def get_det(r):
    det = (r.get("determination") or r.get("decision") or r.get("verdict") or
           r.get("status") or r.get("classification") or "")
    det = det.lower().strip()
    if det in ("reject", "not authentic", "discard", "not_authentic"):
        return "discard"
    elif det in ("review", "concerning"):
        return "review"
    elif det in ("keep", "authentic"):
        return "keep"
    return det


def load_dets(ds_dir):
    det_dir = ds_dir / "final_determinations"
    if not det_dir.exists():
        return {}
    records = {}
    for f in sorted(det_dir.glob("*.ndjson")):
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                    rid = r.get("respondent_id", "")
                    if rid:
                        records[rid] = {
                            "det": get_det(r),
                            "just": r.get("justification", "")[:300],
                        }
                except:
                    continue
    return records


def main():
    # Load client annotations
    client = {}
    with open(SIGNAL_MAP) as f:
        for row in csv.DictReader(f):
            if row["dataset"] == DATASET:
                client[row["respondent_key"]] = {
                    "status": int(row["status"]),
                    "signals": row["signals"].split("; ") if row["signals"] else [],
                    "signal_count": int(row["signal_count"]),
                }
    
    # Load v1 and v2 determinations
    v1 = load_dets(V1_DIR)
    v2 = load_dets(V2_DIR)
    
    print(f"Client annotations: {len(client)}")
    print(f"V1 determinations: {len(v1)}")
    print(f"V2 determinations: {len(v2)}")
    
    # Compute metrics for each version
    def compute_metrics(dets, label):
        tp = fp = fn = tn = 0
        det_counts = Counter()
        for rid, c in client.items():
            if rid not in dets:
                continue
            d = dets[rid]["det"]
            det_counts[d] += 1
            c_rej = c["status"] == 5
            if c_rej and d == "discard":
                tp += 1
            elif not c_rej and d == "discard":
                fp += 1
            elif c_rej and d != "discard":
                fn += 1
            else:
                tn += 1
        
        total = tp + fp + fn + tn
        prec = tp / (tp + fp) * 100 if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) * 100 if (tp + fn) > 0 else 0
        f1 = 2 * prec * recall / (prec + recall) if (prec + recall) > 0 else 0
        acc = (tp + tn) / total * 100 if total > 0 else 0
        disc_rate = (tp + fp) / total * 100 if total > 0 else 0
        
        print(f"\n{'='*80}")
        print(f"{label}")
        print(f"{'='*80}")
        print(f"  Matched: {total}/{len(client)}")
        print(f"  Determinations: {dict(det_counts.most_common())}")
        print(f"  Discard rate: {disc_rate:.1f}% (target: 25.7%)")
        print(f"  TP={tp} FP={fp} FN={fn} TN={tn}")
        print(f"  Precision: {prec:.1f}%")
        print(f"  Recall: {recall:.1f}%")
        print(f"  F1: {f1:.1f}%")
        print(f"  Accuracy: {acc:.1f}%")
        
        return {"tp": tp, "fp": fp, "fn": fn, "tn": tn, "prec": prec, "recall": recall, "f1": f1, "acc": acc, "disc_rate": disc_rate, "det_counts": det_counts}
    
    m1 = compute_metrics(v1, "V1 (without client signals)")
    m2 = compute_metrics(v2, "V2 (with client signals)")
    
    # Comparison
    print(f"\n{'='*80}")
    print(f"COMPARISON: V1 vs V2")
    print(f"{'='*80}")
    print(f"{'Metric':<20} {'V1':>10} {'V2':>10} {'Delta':>10}")
    print(f"{'-'*20} {'-'*10} {'-'*10} {'-'*10}")
    for metric, v1v, v2v in [
        ("Discard rate", m1["disc_rate"], m2["disc_rate"]),
        ("Precision", m1["prec"], m2["prec"]),
        ("Recall", m1["recall"], m2["recall"]),
        ("F1", m1["f1"], m2["f1"]),
        ("Accuracy", m1["acc"], m2["acc"]),
        ("TP", m1["tp"], m2["tp"]),
        ("FP", m1["fp"], m2["fp"]),
        ("FN", m1["fn"], m2["fn"]),
    ]:
        delta = v2v - v1v
        sign = "+" if delta >= 0 else ""
        if isinstance(v1v, float):
            print(f"{metric:<20} {v1v:>9.1f}% {v2v:>9.1f}% {sign}{delta:>8.1f}%")
        else:
            print(f"{metric:<20} {v1v:>10} {v2v:>10} {sign}{delta:>9}")
    
    # Confusion matrix: V2 vs client
    print(f"\n{'='*80}")
    print(f"V2 CONFUSION MATRIX (vs client)")
    print(f"{'='*80}")
    print(f"{'':>20} {'Client Accept':>15} {'Client Reject':>15}")
    print(f"{'Agent Keep':>20} {m2['tn']:>15} {m2['fn']:>15}")
    print(f"{'Agent Review':>20} {'?':>15} {'?':>15}")
    print(f"{'Agent Discard':>20} {m2['fp']:>15} {m2['tp']:>15}")
    
    # Break down review cases
    review_accept = sum(1 for rid, c in client.items() if rid in v2 and v2[rid]["det"] == "review" and c["status"] == 3)
    review_reject = sum(1 for rid, c in client.items() if rid in v2 and v2[rid]["det"] == "review" and c["status"] == 5)
    print(f"\nReview pool: {review_accept} accepts, {review_reject} rejects")
    
    # False negative analysis: what did V2 still miss?
    print(f"\n{'='*80}")
    print(f"V2 FALSE NEGATIVES (client rejected, agent kept/reviewed)")
    print(f"{'='*80}")
    fn_keep = [(rid, c) for rid, c in client.items() if rid in v2 and c["status"] == 5 and v2[rid]["det"] == "keep"]
    fn_review = [(rid, c) for rid, c in client.items() if rid in v2 and c["status"] == 5 and v2[rid]["det"] == "review"]
    print(f"  FN-keep: {len(fn_keep)}")
    print(f"  FN-review: {len(fn_review)}")
    
    fn_signals = Counter()
    for rid, c in fn_keep + fn_review:
        for s in c["signals"]:
            fn_signals[s] += 1
    print(f"\n  Top signals in V2 false negatives:")
    for s, cnt in fn_signals.most_common(15):
        print(f"    {s}: {cnt}")
    
    # False positive analysis
    print(f"\n{'='*80}")
    print(f"V2 FALSE POSITIVES (agent discarded, client accepted)")
    print(f"{'='*80}")
    fp_list = [(rid, c) for rid, c in client.items() if rid in v2 and c["status"] == 3 and v2[rid]["det"] == "discard"]
    print(f"  Count: {len(fp_list)}")
    fp_signals = Counter()
    for rid, c in fp_list:
        for s in c["signals"]:
            fp_signals[s] += 1
    print(f"\n  Top signals in V2 false positives:")
    for s, cnt in fp_signals.most_common(15):
        print(f"    {s}: {cnt}")


if __name__ == "__main__":
    main()
