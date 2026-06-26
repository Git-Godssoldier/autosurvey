#!/usr/bin/env python3
"""Analyze false negatives and false positives in under/over-discarding datasets
to identify patterns for calibration improvement."""

import json
import csv
from pathlib import Path
from collections import Counter, defaultdict

V2_BASE = Path("/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/blind-runs-agent-v2")
SIGNAL_MAP = "/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/status-ground-truth-calibration/core_loop_2026-06-24/status_respondent_signal_map.csv"

DATASET_MAP = {
    "287-2501 THD Digital CX": "251101_THD CX.xlsx",
    "159-2602 Oldcastle Canada": "260401_ OC CAN.xlsx",
    "159-2601 Oldcastle Brand Health": "260206_OC BH.xlsx",
    "189-2501 SBD Brand Association": "260200_SBD.xlsx",
}

TIER1 = {"termflags_nonzero", "long_low_specificity_text", "ai_or_overpolished_text_marker", "generic_placeholder_open_end"}
TIER2 = {"rd_searchr3_canada", "rd_searchr1_22", "rd_searchr1_23", "rd_searchr1_20", "qtime_under_dataset_p10"}
TIER3 = {"duplicate_open_end_text", "rd_review_nonzero", "matrix_near_straightline", "rd_searchr3_united states",
          "qtime_5_to_10_minutes", "qtime_under_4_minutes", "very_short_required_open_end"}

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

def classify_signals(signal_str):
    sigs = set(s.strip() for s in signal_str.split(";") if s.strip())
    t1 = sigs & TIER1
    t2 = sigs & TIER2
    t3 = sigs & TIER3
    other = sigs - TIER1 - TIER2 - TIER3
    return t1, t2, t3, other, sigs

def load_staged(v2_dir):
    """Load staged packets to get answer chains."""
    staged = {}
    staged_file = v2_dir / "staged_packets.ndjson"
    if staged_file.exists():
        with open(staged_file) as f:
            for line in f:
                if line.strip():
                    p = json.loads(line)
                    staged[p["respondent_id"]] = p
    else:
        # Try chunks
        chunks_dir = v2_dir / "chunks"
        if chunks_dir.exists():
            for cf in sorted(chunks_dir.glob("*.ndjson")):
                with open(cf) as f:
                    for line in f:
                        if line.strip():
                            p = json.loads(line)
                            staged[p["respondent_id"]] = p
    return staged

def get_open_end(answer_chain):
    """Extract open-end responses from answer chain."""
    if not answer_chain:
        return ""
    open_ends = []
    if isinstance(answer_chain, list):
        for item in answer_chain:
            if item.get("answer_type") == "open" or "oe" in item.get("field", "").lower():
                val = item.get("label") or item.get("raw_value") or ""
                if val and val.strip():
                    open_ends.append(val.strip())
    elif isinstance(answer_chain, dict):
        for k, v in answer_chain.items():
            if "oe" in k.lower() or "open" in k.lower() or "q14" in k.lower():
                if v and str(v).strip():
                    open_ends.append(str(v).strip())
    return " | ".join(open_ends[:3]) if open_ends else ""

def analyze_dataset(v2_dir_name, signal_map_name):
    v2_dir = V2_BASE / v2_dir_name
    if not v2_dir.exists():
        print(f"  SKIP: {v2_dir_name}")
        return

    # Load determinations
    dets = {}
    for f in sorted((v2_dir / "final_determinations").glob("*.ndjson")):
        with open(f) as fh:
            for line in fh:
                if line.strip():
                    d = json.loads(line)
                    rid = d.get("respondent_id") or d.get("id")
                    dets[rid] = d

    # Load staged packets
    staged = load_staged(v2_dir)

    # Load client annotations
    client = {}
    with open(SIGNAL_MAP) as f:
        for row in csv.DictReader(f):
            if row["dataset"] == signal_map_name:
                client[row["respondent_key"]] = row

    # Classify
    tp_list = []
    fp_list = []
    fn_keep_list = []
    fn_review_list = []
    tn_list = []

    for rid, c in client.items():
        if rid not in dets:
            continue
        agent_det = get_det(dets[rid])
        client_rejected = c["tfg_decision"] == "rejected"
        t1, t2, t3, other, all_sigs = classify_signals(c["signals"])
        
        s = staged.get(rid, {})
        open_end = get_open_end(s.get("answer_chain", []))
        just = dets[rid].get("justification", "")[:300]
        supplier = s.get("supplier", "Unknown")
        risk = s.get("supplier_risk_level", "unknown")
        reject_rate = s.get("supplier_reject_rate", 0)
        timing = s.get("timing_percentile", "unknown")
        qtime = s.get("qtime_seconds", s.get("qtime", 0))

        entry = {
            "rid": rid,
            "agent_det": agent_det,
            "client": c["tfg_decision"],
            "signals": c["signals"],
            "t1": t1, "t2": t2, "t3": t3, "other": other,
            "signal_count": int(c["signal_count"]),
            "supplier": supplier,
            "risk": risk,
            "reject_rate": reject_rate,
            "timing": timing,
            "qtime": qtime,
            "open_end": open_end[:200],
            "justification": just,
        }

        if agent_det == "discard" and client_rejected:
            tp_list.append(entry)
        elif agent_det == "discard" and not client_rejected:
            fp_list.append(entry)
        elif agent_det == "keep" and client_rejected:
            fn_keep_list.append(entry)
        elif agent_det == "keep" and not client_rejected:
            tn_list.append(entry)
        elif agent_det == "review" and client_rejected:
            fn_review_list.append(entry)

    # Print summary
    total = len(tp_list) + len(fp_list) + len(tn_list) + len(fn_keep_list) + len(fn_review_list)
    print(f"\n{'='*100}")
    print(f"DATASET: {v2_dir_name}")
    print(f"  Total matched: {total}")
    print(f"  TP={len(tp_list)} FP={len(fp_list)} TN={len(tn_list)} FN-keep={len(fn_keep_list)} FN-review={len(fn_review_list)}")
    print(f"  Agent discards: {len(tp_list)+len(fp_list)} ({(len(tp_list)+len(fp_list))/total:.1%})")
    print(f"  Client rejects: {len(tp_list)+len(fn_keep_list)+len(fn_review_list)} ({(len(tp_list)+len(fn_keep_list)+len(fn_review_list))/total:.1%})")

    # Analyze FALSE NEGATIVES (missed discards)
    print(f"\n  --- FALSE NEGATIVES (kept/reviewed but client rejected): {len(fn_keep_list)+len(fn_review_list)} ---")
    
    # Signal distribution in FNs
    fn_all = fn_keep_list + fn_review_list
    sig_counter = Counter()
    t1_count = 0
    t2_count = 0
    t3_only_count = 0
    no_signal_count = 0
    for e in fn_all:
        if e["t1"]:
            t1_count += 1
        if e["t2"]:
            t2_count += 1
        if not e["t1"] and not e["t2"] and e["t3"]:
            t3_only_count += 1
        if not e["t1"] and not e["t2"] and not e["t3"]:
            no_signal_count += 1
        for s in e["signals"].split(";"):
            s = s.strip()
            if s:
                sig_counter[s] += 1

    print(f"  FN signal tier breakdown:")
    print(f"    TIER 1 present: {t1_count}")
    print(f"    TIER 2 present (any): {t2_count}")
    print(f"    TIER 3 only: {t3_only_count}")
    print(f"    No classified signals: {no_signal_count}")
    print(f"  FN top signals:")
    for sig, cnt in sig_counter.most_common(10):
        print(f"    {sig}: {cnt}")

    # Supplier distribution in FNs
    supp_counter = Counter(e["supplier"] for e in fn_all)
    print(f"  FN top suppliers:")
    for supp, cnt in supp_counter.most_common(5):
        print(f"    {supp}: {cnt}")

    # Timing distribution in FNs
    timing_counter = Counter(e["timing"] for e in fn_all)
    print(f"  FN timing distribution:")
    for t, cnt in timing_counter.most_common():
        print(f"    {t}: {cnt}")

    # Open-end analysis in FNs
    short_oe = sum(1 for e in fn_all if len(e["open_end"]) < 30 and e["open_end"])
    no_oe = sum(1 for e in fn_all if not e["open_end"])
    print(f"  FN open-end analysis:")
    print(f"    No open-end found: {no_oe}")
    print(f"    Short open-end (<30 chars): {short_oe}")

    # Sample FNs
    print(f"\n  Sample FALSE NEGATIVES (first 10):")
    for e in fn_all[:10]:
        print(f"    {e['rid']}: signals={e['signals'][:80]}")
        print(f"      supplier={e['supplier']}({e['risk']},{e['reject_rate']}%) timing={e['timing']} qtime={e['qtime']}s")
        print(f"      open_end: '{e['open_end'][:100]}'")
        print(f"      agent: {e['agent_det']}, just: {e['justification'][:150]}")
        print()

    # Analyze FALSE POSITIVES (wrong discards)
    print(f"\n  --- FALSE POSITIVES (discarded but client accepted): {len(fp_list)} ---")
    
    sig_counter_fp = Counter()
    t1_count_fp = 0
    t2_count_fp = 0
    t3_only_count_fp = 0
    for e in fp_list:
        if e["t1"]:
            t1_count_fp += 1
        if e["t2"]:
            t2_count_fp += 1
        if not e["t1"] and not e["t2"] and e["t3"]:
            t3_only_count_fp += 1
        for s in e["signals"].split(";"):
            s = s.strip()
            if s:
                sig_counter_fp[s] += 1

    print(f"  FP signal tier breakdown:")
    print(f"    TIER 1 present: {t1_count_fp}")
    print(f"    TIER 2 present (any): {t2_count_fp}")
    print(f"    TIER 3 only: {t3_only_count_fp}")
    print(f"  FP top signals:")
    for sig, cnt in sig_counter_fp.most_common(10):
        print(f"    {sig}: {cnt}")

    # Sample FPs
    print(f"\n  Sample FALSE POSITIVES (first 5):")
    for e in fp_list[:5]:
        print(f"    {e['rid']}: signals={e['signals'][:80]}")
        print(f"      supplier={e['supplier']}({e['risk']},{e['reject_rate']}%) timing={e['timing']}")
        print(f"      open_end: '{e['open_end'][:100]}'")
        print(f"      just: {e['justification'][:150]}")
        print()

    return {
        "dataset": v2_dir_name,
        "fn_count": len(fn_keep_list) + len(fn_review_list),
        "fp_count": len(fp_list),
        "fn_samples": fn_all[:20],
        "fp_samples": fp_list[:20],
    }

def main():
    results = []
    for v2_dir_name, signal_map_name in DATASET_MAP.items():
        r = analyze_dataset(v2_dir_name, signal_map_name)
        if r:
            results.append(r)

    # Cross-dataset FN pattern summary
    print(f"\n{'='*100}")
    print("CROSS-DATASET FN PATTERN SUMMARY")
    print(f"{'='*100}")
    for r in results:
        print(f"  {r['dataset']}: FN={r['fn_count']}, FP={r['fp_count']}")

if __name__ == "__main__":
    main()
