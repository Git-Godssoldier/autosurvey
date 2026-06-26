#!/usr/bin/env python3
"""Aggregate v2 pipeline results across all 11 datasets and compare against client annotations."""

import json
import csv
from pathlib import Path
from collections import defaultdict, Counter

V2_BASE = Path("/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/blind-runs-agent-v2")
SIGNAL_MAP = "/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/status-ground-truth-calibration/core_loop_2026-06-24/status_respondent_signal_map.csv"

# Dataset name mapping: v2 dir name -> signal map dataset name
DATASET_MAP = {
    "106-2502 Delta Water Filtration": "260111_Delta Water Filtration.xlsx",
    "109-2601 Echo BH": "260300_ECHO.xlsx",
    "153-2602 ODL Switchable Glass": "260501_ODL.xlsx",
    "159-2601 Oldcastle Brand Health": "260206_OC BH.xlsx",
    "159-2602 Oldcastle Canada": "260401_ OC CAN.xlsx",
    "189-2501 SBD Brand Association": "260200_SBD.xlsx",
    "287-2501 THD Digital CX": "251101_THD CX.xlsx",
    "365-2601 ADDO RaceTrac US GP": "260404_ADDO.xlsx",
    "368-2602 Masterlock Conjoint": "260403_Masterlock Conjoint.xlsx",
    "999-2601 TFG Contractor Index Q1": "251205_TFG Contractor Index Q1.xlsx",
    "999-2602 TFG Contractor Index Q2": "260306_TFG Contractor Index Q2.xlsx",
}

def get_det(r):
    det = (r.get("determination") or r.get("decision") or r.get("verdict") or
           r.get("status") or r.get("classification") or r.get("disposition") or "")
    det = det.lower().strip()
    if det in ("reject", "not authentic", "discard", "not_authentic"):
        return "discard"
    elif det in ("review", "concerning"):
        return "review"
    elif det in ("keep", "authentic"):
        return "keep"
    return det

def main():
    # Load client annotations
    client = defaultdict(dict)
    with open(SIGNAL_MAP) as f:
        for row in csv.DictReader(f):
            ds = row["dataset"]
            rid = row["respondent_key"]
            client[ds][rid] = {
                "tfg_decision": row["tfg_decision"],
                "signals": row["signals"],
                "signal_count": int(row["signal_count"]),
            }

    # Aggregate results
    all_results = []
    per_dataset = {}

    for v2_dir_name, signal_map_name in DATASET_MAP.items():
        v2_dir = V2_BASE / v2_dir_name
        if not v2_dir.exists():
            print(f"SKIP: {v2_dir_name} (directory not found)")
            continue

        # Load all determinations
        dets = {}
        for f in sorted((v2_dir / "final_determinations").glob("*.ndjson")):
            with open(f) as fh:
                for line in fh:
                    if line.strip():
                        d = json.loads(line)
                        rid = d.get("respondent_id") or d.get("id")
                        dets[rid] = d

        # Compare against client annotations
        sm = client.get(signal_map_name, {})
        if not sm:
            print(f"SKIP: {v2_dir_name} (no client annotations found as '{signal_map_name}')")
            continue

        tp = fp = tn = fn_keep = fn_review = 0
        agent_discards = 0
        agent_keeps = 0
        agent_reviews = 0
        total = 0

        for rid, c in sm.items():
            if rid not in dets:
                continue
            total += 1
            agent_det = get_det(dets[rid])
            client_rejected = c["tfg_decision"] == "rejected"

            if agent_det == "discard":
                agent_discards += 1
                if client_rejected:
                    tp += 1
                else:
                    fp += 1
            elif agent_det == "keep":
                agent_keeps += 1
                if client_rejected:
                    fn_keep += 1
                else:
                    tn += 1
            elif agent_det == "review":
                agent_reviews += 1
                if client_rejected:
                    fn_review += 1
                else:
                    tn += 1  # Review + client kept = correct

        client_rejects = sum(1 for c in sm.values() if c["tfg_decision"] == "rejected")
        client_accepts = sum(1 for c in sm.values() if c["tfg_decision"] == "accepted")
        matched = total

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn_keep + fn_review) if (tp + fn_keep + fn_review) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        accuracy = (tp + tn) / matched if matched > 0 else 0
        discard_rate = agent_discards / matched if matched > 0 else 0
        client_reject_rate = client_rejects / len(sm) if len(sm) > 0 else 0

        ds_result = {
            "dataset": v2_dir_name,
            "signal_map_name": signal_map_name,
            "total_respondents": len(sm),
            "matched": matched,
            "agent_discards": agent_discards,
            "agent_keeps": agent_keeps,
            "agent_reviews": agent_reviews,
            "client_rejects": client_rejects,
            "client_accepts": client_accepts,
            "tp": tp,
            "fp": fp,
            "tn": tn,
            "fn_keep": fn_keep,
            "fn_review": fn_review,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "accuracy": accuracy,
            "discard_rate": discard_rate,
            "client_reject_rate": client_reject_rate,
        }
        per_dataset[v2_dir_name] = ds_result
        all_results.append(ds_result)

    # Print per-dataset results
    print("=" * 120)
    print(f"{'Dataset':<45} {'Matched':>7} {'Disc%':>6} {'Client%':>7} {'TP':>4} {'FP':>4} {'TN':>4} {'FN-K':>5} {'FN-R':>5} {'Prec':>6} {'Recall':>7} {'F1':>6} {'Acc':>6}")
    print("=" * 120)
    for r in all_results:
        print(f"{r['dataset']:<45} {r['matched']:>7} {r['discard_rate']:>5.1%} {r['client_reject_rate']:>6.1%} "
              f"{r['tp']:>4} {r['fp']:>4} {r['tn']:>4} {r['fn_keep']:>5} {r['fn_review']:>5} "
              f"{r['precision']:>5.1%} {r['recall']:>6.1%} {r['f1']:>5.1%} {r['accuracy']:>5.1%}")

    # Aggregate
    total_tp = sum(r["tp"] for r in all_results)
    total_fp = sum(r["fp"] for r in all_results)
    total_tn = sum(r["tn"] for r in all_results)
    total_fn_keep = sum(r["fn_keep"] for r in all_results)
    total_fn_review = sum(r["fn_review"] for r in all_results)
    total_matched = sum(r["matched"] for r in all_results)
    total_discards = sum(r["agent_discards"] for r in all_results)
    total_client_rejects = sum(r["client_rejects"] for r in all_results)
    total_respondents = sum(r["total_respondents"] for r in all_results)

    agg_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
    agg_recall = total_tp / (total_tp + total_fn_keep + total_fn_review) if (total_tp + total_fn_keep + total_fn_review) > 0 else 0
    agg_f1 = 2 * agg_precision * agg_recall / (agg_precision + agg_recall) if (agg_precision + agg_recall) > 0 else 0
    agg_accuracy = (total_tp + total_tn) / total_matched if total_matched > 0 else 0
    agg_discard_rate = total_discards / total_matched if total_matched > 0 else 0
    agg_client_reject_rate = total_client_rejects / total_respondents if total_respondents > 0 else 0

    print("=" * 120)
    print(f"{'AGGREGATE (11 datasets)':<45} {total_matched:>7} {agg_discard_rate:>5.1%} {agg_client_reject_rate:>6.1%} "
          f"{total_tp:>4} {total_fp:>4} {total_tn:>4} {total_fn_keep:>5} {total_fn_review:>5} "
          f"{agg_precision:>5.1%} {agg_recall:>6.1%} {agg_f1:>5.1%} {agg_accuracy:>5.1%}")
    print("=" * 120)

    # Check for incomplete datasets
    print("\n=== COMPLETENESS CHECK ===")
    for v2_dir_name in DATASET_MAP:
        v2_dir = V2_BASE / v2_dir_name
        if not v2_dir.exists():
            print(f"  MISSING: {v2_dir_name}")
            continue
        chunks = len(list((v2_dir / "chunks").glob("*.ndjson"))) if (v2_dir / "chunks").exists() else 0
        dets = len(list((v2_dir / "final_determinations").glob("*.ndjson"))) if (v2_dir / "final_determinations").exists() else 0
        if chunks != dets:
            print(f"  INCOMPLETE: {v2_dir_name} — {chunks} chunks, {dets} determinations ({chunks - dets} missing)")
        else:
            print(f"  COMPLETE: {v2_dir_name} — {chunks} chunks, {dets} determinations")

    # Save JSON report
    report = {
        "per_dataset": all_results,
        "aggregate": {
            "total_respondents": total_respondents,
            "total_matched": total_matched,
            "total_tp": total_tp,
            "total_fp": total_fp,
            "total_tn": total_tn,
            "total_fn_keep": total_fn_keep,
            "total_fn_review": total_fn_review,
            "precision": agg_precision,
            "recall": agg_recall,
            "f1": agg_f1,
            "accuracy": agg_accuracy,
            "discard_rate": agg_discard_rate,
            "client_reject_rate": agg_client_reject_rate,
        },
    }
    report_path = V2_BASE / "v2_aggregate_report.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nReport saved to: {report_path}")

if __name__ == "__main__":
    main()
