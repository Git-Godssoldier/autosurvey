#!/usr/bin/env python3
"""Compare agent determinations against client ground-truth annotations across all datasets."""

import json
import csv
import os
from pathlib import Path
from collections import Counter, defaultdict

# Map client dataset names to our blind-run directory names
DATASET_MAP = {
    "260111_Delta Water Filtration.xlsx": "106-2502 Delta Water Filtration",
    "260206_OC BH.xlsx": "159-2601 Oldcastle Brand Health",
    "251101_THD CX.xlsx": "287-2501 THD Digital CX",
    "260300_ECHO.xlsx": "109-2601 Echo BH",
    "260404_ADDO.xlsx": "365-2601 ADDO RaceTrac US GP",
    "260306_TFG Contractor Index Q2.xlsx": "999-2602 TFG Contractor Index Q2",
    "260403_Masterlock Conjoint.xlsx": "368-2602 Masterlock Conjoint",
    "251205_TFG Contractor Index Q1.xlsx": "999-2601 TFG Contractor Index Q1",
    "260200_SBD.xlsx": "189-2501 SBD Brand Association",
    "260401_ OC CAN.xlsx": "159-2602 Oldcastle Canada",
    "260501_ODL.xlsx": "153-2602 ODL Switchable Glass",
}

SIGNAL_MAP = "/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/status-ground-truth-calibration/core_loop_2026-06-24/status_respondent_signal_map.csv"
BLIND_BASE = Path("/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/blind-runs-agent")


def get_determination(record):
    """Extract determination from record, handling schema variations."""
    det = (record.get("determination") or record.get("decision") or
           record.get("verdict") or record.get("status") or
           record.get("classification") or "")
    det = det.lower().strip()
    if det in ("reject", "not authentic", "discard", "not_authentic"):
        return "discard"
    elif det in ("review", "concerning"):
        return "review"
    elif det in ("keep", "authentic"):
        return "keep"
    return det


def load_client_annotations():
    """Load client status annotations from the signal map CSV."""
    annotations = {}  # dataset_name -> {respondent_key: {status, decision, signals}}
    with open(SIGNAL_MAP) as f:
        reader = csv.DictReader(f)
        for row in reader:
            ds = row["dataset"]
            if ds not in annotations:
                annotations[ds] = {}
            key = row["respondent_key"]
            status = int(row["status"])
            annotations[ds][key] = {
                "status": status,
                "decision": row["tfg_decision"],
                "signals": row["signals"].split("; ") if row["signals"] else [],
                "source_row": int(row["source_row_number"]),
            }
    return annotations


def load_agent_determinations(dataset_dir):
    """Load all agent determinations for a dataset."""
    det_dir = dataset_dir / "final_determinations"
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
                            "determination": get_determination(r),
                            "justification": r.get("justification", ""),
                            "raw": r,
                        }
                except json.JSONDecodeError:
                    continue
    return records


def compute_metrics(client, agent):
    """Compute precision, recall, F1 for discard decisions."""
    tp = 0  # client reject + agent discard
    fp = 0  # client accept + agent discard
    fn = 0  # client reject + agent NOT discard
    tn = 0  # client accept + agent NOT discard
    
    flagged_tp = 0  # client reject + agent (discard or review)
    flagged_fp = 0  # client accept + agent (discard or review)
    
    for key, c in client.items():
        if key not in agent:
            continue
        a_det = agent[key]["determination"]
        c_reject = (c["status"] == 5)
        
        if c_reject and a_det == "discard":
            tp += 1
        elif not c_reject and a_det == "discard":
            fp += 1
        elif c_reject and a_det != "discard":
            fn += 1
        else:
            tn += 1
        
        if c_reject and a_det in ("discard", "review"):
            flagged_tp += 1
        elif not c_reject and a_det in ("discard", "review"):
            flagged_fp += 1
    
    total = tp + fp + fn + tn
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    flagged_precision = flagged_tp / (flagged_tp + flagged_fp) if (flagged_tp + flagged_fp) > 0 else 0
    flagged_recall = flagged_tp / (flagged_tp + fn) if (flagged_tp + fn) > 0 else 0
    flagged_f1 = 2 * flagged_precision * flagged_recall / (flagged_precision + flagged_recall) if (flagged_precision + flagged_recall) > 0 else 0
    
    accuracy = (tp + tn) / total if total > 0 else 0  # accuracy to client discards
    
    return {
        "total": total,
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
        "precision": round(precision * 100, 1),
        "recall": round(recall * 100, 1),
        "f1": round(f1 * 100, 1),
        "accuracy": round(accuracy * 100, 1),
        "flagged_tp": flagged_tp, "flagged_fp": flagged_fp,
        "flagged_precision": round(flagged_precision * 100, 1),
        "flagged_recall": round(flagged_recall * 100, 1),
        "flagged_f1": round(flagged_f1 * 100, 1),
        "client_reject_rate": round((tp + fn) / total * 100, 1) if total > 0 else 0,
        "agent_discard_rate": round((tp + fp) / total * 100, 1) if total > 0 else 0,
    }


def analyze_false_negatives(client, agent):
    """Analyze client rejects that the agent kept or reviewed."""
    fn_keep = []  # client reject + agent keep
    fn_review = []  # client reject + agent review
    for key, c in client.items():
        if key not in agent:
            continue
        if c["status"] == 5:
            a_det = agent[key]["determination"]
            if a_det == "keep":
                fn_keep.append((key, c, agent[key]))
            elif a_det == "review":
                fn_review.append((key, c, agent[key]))
    return fn_keep, fn_review


def analyze_false_positives(client, agent):
    """Analyze client accepts that the agent discarded."""
    fp_list = []
    for key, c in client.items():
        if key not in agent:
            continue
        if c["status"] == 3 and agent[key]["determination"] == "discard":
            fp_list.append((key, c, agent[key]))
    return fp_list


def aggregate_signals(fn_cases, label):
    """Aggregate client signals from false negative cases."""
    signal_counts = Counter()
    for key, c, a in fn_cases:
        for s in c["signals"]:
            signal_counts[s] += 1
    print(f"\n  Client signals in {label} ({len(fn_cases)} cases):")
    for sig, cnt in signal_counts.most_common(20):
        print(f"    {sig}: {cnt}")


def main():
    client_data = load_client_annotations()
    
    print("=" * 130)
    print("AGENT vs CLIENT GROUND TRUTH — ALL 11 DATASETS")
    print("=" * 130)
    
    all_metrics = {}
    all_fn_keep = []
    all_fn_review = []
    all_fp = []
    total_matched = 0
    
    # Header
    print(f"\n{'Dataset':<45} {'Matched':>7} {'Client%':>7} {'Agent%':>7} {'Prec':>6} {'Recall':>7} {'F1':>6} {'Acc':>6} {'FPrec':>7} {'FRec':>7} {'FF1':>6}")
    print(f"{'-'*45} {'-'*7} {'-'*7} {'-'*7} {'-'*6} {'-'*7} {'-'*6} {'-'*6} {'-'*7} {'-'*7} {'-'*6}")
    
    for client_ds, blind_ds in sorted(DATASET_MAP.items()):
        if client_ds not in client_data:
            print(f"WARNING: No client data for {client_ds}")
            continue
        
        blind_dir = BLIND_BASE / blind_ds
        agent_dets = load_agent_determinations(blind_dir)
        client_ann = client_data[client_ds]
        
        # Match
        matched = sum(1 for k in client_ann if k in agent_dets)
        total_matched += matched
        
        metrics = compute_metrics(client_ann, agent_dets)
        all_metrics[blind_ds] = metrics
        
        print(f"{blind_ds:<45} {matched:>7} {metrics['client_reject_rate']:>6.1f}% {metrics['agent_discard_rate']:>6.1f}% {metrics['precision']:>5.1f}% {metrics['recall']:>6.1f}% {metrics['f1']:>5.1f}% {metrics['accuracy']:>5.1f}% {metrics['flagged_precision']:>6.1f}% {metrics['flagged_recall']:>6.1f}% {metrics['flagged_f1']:>5.1f}%")
        
        # Collect false negatives and false positives
        fn_keep, fn_review = analyze_false_negatives(client_ann, agent_dets)
        fp_list = analyze_false_positives(client_ann, agent_dets)
        all_fn_keep.extend([(blind_ds, *fn) for fn in fn_keep])
        all_fn_review.extend([(blind_ds, *fn) for fn in fn_review])
        all_fp.extend([(blind_ds, *fp) for fp in fp_list])
    
    # Totals
    total_tp = sum(m["tp"] for m in all_metrics.values())
    total_fp = sum(m["fp"] for m in all_metrics.values())
    total_fn = sum(m["fn"] for m in all_metrics.values())
    total_tn = sum(m["tn"] for m in all_metrics.values())
    total_flagged_tp = sum(m["flagged_tp"] for m in all_metrics.values())
    total_flagged_fp = sum(m["flagged_fp"] for m in all_metrics.values())
    
    total_prec = total_tp / (total_tp + total_fp) * 100 if (total_tp + total_fp) > 0 else 0
    total_rec = total_tp / (total_tp + total_fn) * 100 if (total_tp + total_fn) > 0 else 0
    total_f1 = 2 * total_prec * total_rec / (total_prec + total_rec) if (total_prec + total_rec) > 0 else 0
    total_acc = (total_tp + total_tn) / total_matched * 100 if total_matched > 0 else 0
    total_fprec = total_flagged_tp / (total_flagged_tp + total_flagged_fp) * 100 if (total_flagged_tp + total_flagged_fp) > 0 else 0
    total_frec = total_flagged_tp / (total_flagged_tp + total_fn) * 100 if (total_flagged_tp + total_fn) > 0 else 0
    total_ff1 = 2 * total_fprec * total_frec / (total_fprec + total_frec) if (total_fprec + total_frec) > 0 else 0
    
    print(f"{'-'*45} {'-'*7} {'-'*7} {'-'*7} {'-'*6} {'-'*7} {'-'*6} {'-'*6} {'-'*7} {'-'*7} {'-'*6}")
    client_rej_total = total_tp + total_fn
    agent_disc_total = total_tp + total_fp
    print(f"{'TOTAL':<45} {total_matched:>7} {client_rej_total/total_matched*100:>6.1f}% {agent_disc_total/total_matched*100:>6.1f}% {total_prec:>5.1f}% {total_rec:>6.1f}% {total_f1:>5.1f}% {total_acc:>5.1f}% {total_fprec:>6.1f}% {total_frec:>6.1f}% {total_ff1:>5.1f}%")
    
    # False negative analysis
    print(f"\n{'='*130}")
    print(f"FALSE NEGATIVE ANALYSIS — Client rejects the agent did NOT discard")
    print(f"{'='*130}")
    print(f"\nTotal false negatives (client reject + agent keep): {len(all_fn_keep)}")
    print(f"Total false negatives (client reject + agent review): {len(all_fn_review)}")
    print(f"Total false negatives (all): {len(all_fn_keep) + len(all_fn_review)}")
    print(f"Total false positives (client accept + agent discard): {len(all_fp)}")
    
    # Aggregate signals from false negatives (kept)
    fn_keep_signals = Counter()
    for ds, key, c, a in all_fn_keep:
        for s in c["signals"]:
            fn_keep_signals[s] += 1
    print(f"\n  Client signals in FALSE NEGATIVES (agent kept, client rejected) — {len(all_fn_keep)} cases:")
    for sig, cnt in fn_keep_signals.most_common(30):
        print(f"    {sig}: {cnt}")
    
    # Aggregate signals from false negatives (reviewed)
    fn_review_signals = Counter()
    for ds, key, c, a in all_fn_review:
        for s in c["signals"]:
            fn_review_signals[s] += 1
    print(f"\n  Client signals in FALSE NEGATIVES (agent reviewed, client rejected) — {len(all_fn_review)} cases:")
    for sig, cnt in fn_review_signals.most_common(30):
        print(f"    {sig}: {cnt}")
    
    # Aggregate signals from false positives
    fp_signals = Counter()
    for ds, key, c, a in all_fp:
        for s in c["signals"]:
            fp_signals[s] += 1
    print(f"\n  Client signals in FALSE POSITIVES (agent discarded, client accepted) — {len(all_fp)} cases:")
    for sig, cnt in fp_signals.most_common(30):
        print(f"    {sig}: {cnt}")
    
    # What signals do client rejects have that we're missing?
    all_reject_signals = Counter()
    for ds in client_data:
        for key, c in client_data[ds].items():
            if c["status"] == 5:
                for s in c["signals"]:
                    all_reject_signals[s] += 1
    print(f"\n  ALL client reject signals (ground truth) — {sum(1 for ds in client_data for k,v in client_data[ds].items() if v['status']==5)} total rejects:")
    for sig, cnt in all_reject_signals.most_common(30):
        print(f"    {sig}: {cnt}")
    
    # Per-dataset breakdown of false negatives
    print(f"\n{'='*130}")
    print(f"PER-DATASET FALSE NEGATIVE BREAKDOWN")
    print(f"{'='*130}")
    fn_by_ds = Counter()
    fn_review_by_ds = Counter()
    for ds, key, c, a in all_fn_keep:
        fn_by_ds[ds] += 1
    for ds, key, c, a in all_fn_review:
        fn_review_by_ds[ds] += 1
    print(f"\n{'Dataset':<45} {'FN Keep':>8} {'FN Review':>10} {'Total FN':>9} {'Total Rejects':>14}")
    for ds in sorted(fn_by_ds.keys() | fn_review_by_ds.keys()):
        k = fn_by_ds.get(ds, 0)
        r = fn_review_by_ds.get(ds, 0)
        total_rej = sum(1 for kk, v in client_data[[k for k, v in DATASET_MAP.items() if v == ds][0]].items() if v["status"] == 5)
        print(f"{ds:<45} {k:>8} {r:>10} {k+r:>9} {total_rej:>14}")
    
    # What would get us to 20% discard with >90% accuracy?
    print(f"\n{'='*130}")
    print(f"PATH TO 20% DISCARD WITH >90% ACCURACY")
    print(f"{'='*130}")
    
    current_discard_rate = agent_disc_total / total_matched * 100
    target_discard_rate = 20.0
    target_discards = int(total_matched * target_discard_rate / 100)
    current_discards = total_tp + total_fp
    needed_additional = target_discards - current_discards
    
    print(f"\nCurrent discard rate: {current_discard_rate:.1f}% ({current_discards} discards)")
    print(f"Target discard rate: {target_discard_rate:.1f}% ({target_discards} discards)")
    print(f"Need {needed_additional} more discards")
    print(f"Current accuracy: {total_acc:.1f}%")
    print(f"Target accuracy: >90%")
    
    # How many review cases are client rejects?
    review_rejects = len(all_fn_review)
    review_accepts = sum(1 for ds, key, c, a in all_fn_review if c["status"] == 3)
    # Actually all_fn_review are all client rejects that agent reviewed
    # Let's count how many review cases are client accepts
    total_review = sum(1 for m in all_metrics.values() for _ in range(m["flagged_tp"] - m["tp"] + m["flagged_fp"] - m["fp"]))
    
    print(f"\nIf we converted ALL review→discard for client rejects: +{review_rejects} true positives")
    print(f"If we converted ALL review→discard for client accepts: +{len(all_fp) - 0} false positives (wait, need to recount)")
    
    # Count review cases that are client accepts
    review_accept_count = 0
    review_reject_count = 0
    for client_ds, blind_ds in DATASET_MAP.items():
        if client_ds not in client_data:
            continue
        blind_dir = BLIND_BASE / blind_ds
        agent_dets = load_agent_determinations(blind_dir)
        for key, c in client_data[client_ds].items():
            if key in agent_dets and agent_dets[key]["determination"] == "review":
                if c["status"] == 5:
                    review_reject_count += 1
                else:
                    review_accept_count += 1
    
    print(f"\nReview pool breakdown:")
    print(f"  Review cases that are client rejects: {review_reject_count}")
    print(f"  Review cases that are client accepts: {review_accept_count}")
    print(f"  Total review cases: {review_reject_count + review_accept_count}")
    
    if review_reject_count + review_accept_count > 0:
        review_precision = review_reject_count / (review_reject_count + review_accept_count) * 100
        print(f"  Review precision (if all review→discard): {review_precision:.1f}%")
    
    # Scenario: discard all review cases
    new_tp = total_tp + review_reject_count
    new_fp = total_fp + review_accept_count
    new_discard_rate = (new_tp + new_fp) / total_matched * 100
    new_precision = new_tp / (new_tp + new_fp) * 100 if (new_tp + new_fp) > 0 else 0
    new_recall = new_tp / (total_tp + total_fn) * 100
    new_accuracy = (new_tp + (total_tn - review_accept_count)) / total_matched * 100
    
    print(f"\n  SCENARIO A: Convert ALL review → discard")
    print(f"    Discard rate: {new_discard_rate:.1f}%")
    print(f"    Precision: {new_precision:.1f}%")
    print(f"    Recall: {new_recall:.1f}%")
    print(f"    Accuracy: {new_accuracy:.1f}%")
    
    # Scenario: only convert review cases with specific signals
    # Check which signals in review-rejects are most predictive
    review_reject_signals = Counter()
    review_accept_signals = Counter()
    for client_ds, blind_ds in DATASET_MAP.items():
        if client_ds not in client_data:
            continue
        blind_dir = BLIND_BASE / blind_ds
        agent_dets = load_agent_determinations(blind_dir)
        for key, c in client_data[client_ds].items():
            if key in agent_dets and agent_dets[key]["determination"] == "review":
                if c["status"] == 5:
                    for s in c["signals"]:
                        review_reject_signals[s] += 1
                else:
                    for s in c["signals"]:
                        review_accept_signals[s] += 1
    
    print(f"\n  Signal comparison: Review→Reject vs Review→Accept")
    print(f"  {'Signal':<50} {'Rev→Rej':>8} {'Rev→Acc':>8} {'Precision':>10}")
    all_review_signals = set(review_reject_signals.keys()) | set(review_accept_signals.keys())
    signal_precision = []
    for s in all_review_signals:
        rej = review_reject_signals.get(s, 0)
        acc = review_accept_signals.get(s, 0)
        prec = rej / (rej + acc) * 100 if (rej + acc) > 0 else 0
        signal_precision.append((s, rej, acc, prec))
    
    signal_precision.sort(key=lambda x: x[1], reverse=True)
    for s, rej, acc, prec in signal_precision[:25]:
        print(f"  {s:<50} {rej:>8} {acc:>8} {prec:>9.1f}%")
    
    # Write detailed JSON output
    output = {
        "total_matched": total_matched,
        "total_tp": total_tp,
        "total_fp": total_fp,
        "total_fn": total_fn,
        "total_tn": total_tn,
        "precision": round(total_prec, 1),
        "recall": round(total_rec, 1),
        "f1": round(total_f1, 1),
        "accuracy": round(total_acc, 1),
        "client_reject_rate": round(client_rej_total / total_matched * 100, 1),
        "agent_discard_rate": round(current_discard_rate, 1),
        "per_dataset": all_metrics,
        "false_negative_count": len(all_fn_keep) + len(all_fn_review),
        "false_positive_count": len(all_fp),
        "review_reject_count": review_reject_count,
        "review_accept_count": review_accept_count,
        "scenario_a_all_review_to_discard": {
            "discard_rate": round(new_discard_rate, 1),
            "precision": round(new_precision, 1),
            "recall": round(new_recall, 1),
            "accuracy": round(new_accuracy, 1),
        },
    }
    
    out_path = BLIND_BASE / "agent_vs_client_analysis.json"
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\nDetailed analysis written to: {out_path}")


if __name__ == "__main__":
    main()
