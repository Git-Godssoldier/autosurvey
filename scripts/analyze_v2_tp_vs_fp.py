#!/usr/bin/env python3
"""Analyze what distinguishes V2 true positives from false positives on Delta.
This will help us refine the agent instructions to improve precision."""

import json
import csv
from collections import Counter, defaultdict
from pathlib import Path

SIGNAL_MAP = "/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/status-ground-truth-calibration/core_loop_2026-06-24/status_respondent_signal_map.csv"
V2_DIR = Path("/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/blind-runs-agent-v2/106-2502 Delta Water Filtration")
STAGED = V2_DIR / "staged_packets.ndjson"
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

def main():
    # Load client annotations
    client = {}
    with open(SIGNAL_MAP) as f:
        for row in csv.DictReader(f):
            if row["dataset"] == DATASET:
                client[row["respondent_key"]] = {
                    "status": int(row["status"]),
                    "signals": set(row["signals"].split("; ") if row["signals"] else []),
                    "signal_count": int(row["signal_count"]),
                }

    # Load staged packets (with supplier info, timing, etc.)
    staged = {}
    with open(STAGED) as f:
        for line in f:
            if line.strip():
                p = json.loads(line)
                staged[p["respondent_id"]] = p

    # Load V2 determinations
    v2 = {}
    for f in sorted((V2_DIR / "final_determinations").glob("*.ndjson")):
        with open(f) as fh:
            for line in fh:
                if line.strip():
                    r = json.loads(line)
                    rid = r.get("respondent_id", "")
                    if rid:
                        v2[rid] = {
                            "det": get_det(r),
                            "just": r.get("justification", ""),
                            "raw": r,
                        }

    # Classify V2 discards into TP and FP
    tp_cases = []  # agent discard + client reject
    fp_cases = []  # agent discard + client accept
    fn_keep = []   # agent keep + client reject
    fn_review = [] # agent review + client reject
    tn_cases = []  # agent keep + client accept

    for rid, c in client.items():
        if rid not in v2 or rid not in staged:
            continue
        s = staged[rid]
        a = v2[rid]
        if a["det"] == "discard":
            if c["status"] == 5:
                tp_cases.append((rid, c, s, a))
            else:
                fp_cases.append((rid, c, s, a))
        elif a["det"] == "keep":
            if c["status"] == 5:
                fn_keep.append((rid, c, s, a))
            else:
                tn_cases.append((rid, c, s, a))
        elif a["det"] == "review":
            if c["status"] == 5:
                fn_review.append((rid, c, s, a))

    print(f"V2 Delta Analysis:")
    print(f"  TP (correct discards): {len(tp_cases)}")
    print(f"  FP (wrong discards): {len(fp_cases)}")
    print(f"  FN-keep (missed, kept): {len(fn_keep)}")
    print(f"  FN-review (missed, reviewed): {len(fn_review)}")
    print(f"  TN (correct keeps): {len(tn_cases)}")

    # Compare TP vs FP on various dimensions
    print(f"\n{'='*100}")
    print("DIMENSION 1: Client signal count")
    print(f"{'='*100}")
    tp_sc = [c["signal_count"] for _, c, _, _ in tp_cases]
    fp_sc = [c["signal_count"] for _, c, _, _ in fp_cases]
    fn_sc = [c["signal_count"] for _, c, _, _ in fn_keep + fn_review]
    tn_sc = [c["signal_count"] for _, c, _, _ in tn_cases]
    
    import statistics
    print(f"  TP signal_count: mean={statistics.mean(tp_sc):.1f}, median={statistics.median(tp_sc):.0f}")
    print(f"  FP signal_count: mean={statistics.mean(fp_sc):.1f}, median={statistics.median(fp_sc):.0f}")
    print(f"  FN signal_count: mean={statistics.mean(fn_sc):.1f}, median={statistics.median(fn_sc):.0f}")
    print(f"  TN signal_count: mean={statistics.mean(tn_sc):.1f}, median={statistics.median(tn_sc):.0f}")

    # Signal count distribution
    print(f"\n  Signal count distribution:")
    print(f"  {'Count':>6} {'TP':>5} {'FP':>5} {'FN':>5} {'TN':>5} {'TP%':>6} {'FP%':>6}")
    for sc in range(1, 9):
        tp_n = sum(1 for x in tp_sc if x == sc)
        fp_n = sum(1 for x in fp_sc if x == sc)
        fn_n = sum(1 for x in fn_sc if x == sc)
        tn_n = sum(1 for x in tn_sc if x == sc)
        total = tp_n + fp_n
        tp_pct = tp_n / total * 100 if total > 0 else 0
        print(f"  {sc:>6} {tp_n:>5} {fp_n:>5} {fn_n:>5} {tn_n:>5} {tp_pct:>5.0f}%")

    # Dimension 2: Supplier risk level
    print(f"\n{'='*100}")
    print("DIMENSION 2: Supplier risk level")
    print(f"{'='*100}")
    tp_risk = Counter(s.get("supplier_risk_level", "?") for _, _, s, _ in tp_cases)
    fp_risk = Counter(s.get("supplier_risk_level", "?") for _, _, s, _ in fp_cases)
    fn_risk = Counter(s.get("supplier_risk_level", "?") for _, _, s, _ in fn_keep + fn_review)
    tn_risk = Counter(s.get("supplier_risk_level", "?") for _, _, s, _ in tn_cases)
    
    print(f"  {'Risk':>10} {'TP':>5} {'FP':>5} {'FN':>5} {'TN':>5} {'Precision':>10}")
    for risk in ["high", "medium", "moderate", "low", "unknown"]:
        tp_n = tp_risk.get(risk, 0)
        fp_n = fp_risk.get(risk, 0)
        fn_n = fn_risk.get(risk, 0)
        tn_n = tn_risk.get(risk, 0)
        prec = tp_n / (tp_n + fp_n) * 100 if (tp_n + fp_n) > 0 else 0
        print(f"  {risk:>10} {tp_n:>5} {fp_n:>5} {fn_n:>5} {tn_n:>5} {prec:>9.0f}%")

    # Dimension 3: Timing
    print(f"\n{'='*100}")
    print("DIMENSION 3: Timing percentile")
    print(f"{'='*100}")
    tp_time = Counter(s.get("timing_percentile", "?") for _, _, s, _ in tp_cases)
    fp_time = Counter(s.get("timing_percentile", "?") for _, _, s, _ in fp_cases)
    fn_time = Counter(s.get("timing_percentile", "?") for _, _, s, _ in fn_keep + fn_review)
    tn_time = Counter(s.get("timing_percentile", "?") for _, _, s, _ in tn_cases)
    
    print(f"  {'Percentile':>15} {'TP':>5} {'FP':>5} {'FN':>5} {'TN':>5} {'Precision':>10}")
    for pct in ["bottom_10", "bottom_25", "below_median", "above_median", "top_25", "top_10"]:
        tp_n = tp_time.get(pct, 0)
        fp_n = fp_time.get(pct, 0)
        fn_n = fn_time.get(pct, 0)
        tn_n = tn_time.get(pct, 0)
        prec = tp_n / (tp_n + fp_n) * 100 if (tp_n + fp_n) > 0 else 0
        print(f"  {pct:>15} {tp_n:>5} {fp_n:>5} {fn_n:>5} {tn_n:>5} {prec:>9.0f}%")

    # Dimension 4: Specific client signals
    print(f"\n{'='*100}")
    print("DIMENSION 4: Specific client signals in TP vs FP")
    print(f"{'='*100}")
    tp_sigs = Counter()
    fp_sigs = Counter()
    for _, c, _, _ in tp_cases:
        for s in c["signals"]:
            tp_sigs[s] += 1
    for _, c, _, _ in fp_cases:
        for s in c["signals"]:
            fp_sigs[s] += 1
    
    print(f"  {'Signal':<45} {'TP':>5} {'FP':>5} {'TP%':>6} {'Lift':>6}")
    all_sigs = set(tp_sigs.keys()) | set(fp_sigs.keys())
    for s in sorted(all_sigs, key=lambda x: tp_sigs.get(x, 0) + fp_sigs.get(x, 0), reverse=True)[:20]:
        tp_n = tp_sigs.get(s, 0)
        fp_n = fp_sigs.get(s, 0)
        total = tp_n + fp_n
        tp_pct = tp_n / total * 100 if total > 0 else 0
        # Lift vs base rate (109 TP / 348 total discards = 31.3%)
        lift = tp_pct / 31.3 if tp_pct > 0 else 0
        print(f"  {s:<45} {tp_n:>5} {fp_n:>5} {tp_pct:>5.0f}% {lift:>5.2f}x")

    # Dimension 5: Supplier name
    print(f"\n{'='*100}")
    print("DIMENSION 5: Supplier name (TP vs FP)")
    print(f"{'='*100}")
    tp_sup = Counter(s.get("supplier", "?") for _, _, s, _ in tp_cases)
    fp_sup = Counter(s.get("supplier", "?") for _, _, s, _ in fp_cases)
    
    print(f"  {'Supplier':<45} {'TP':>5} {'FP':>5} {'Precision':>10}")
    all_sup = set(tp_sup.keys()) | set(fp_sup.keys())
    for sup in sorted(all_sup, key=lambda x: tp_sup.get(x, 0) + fp_sup.get(x, 0), reverse=True)[:15]:
        tp_n = tp_sup.get(sup, 0)
        fp_n = fp_sup.get(sup, 0)
        prec = tp_n / (tp_n + fp_n) * 100 if (tp_n + fp_n) > 0 else 0
        print(f"  {str(sup):<45} {tp_n:>5} {fp_n:>5} {prec:>9.0f}%")

    # Dimension 6: Duplicate memberships
    print(f"\n{'='*100}")
    print("DIMENSION 6: Duplicate text memberships")
    print(f"{'='*100}")
    tp_dups = [len(s.get("duplicate_memberships", [])) for _, _, s, _ in tp_cases]
    fp_dups = [len(s.get("duplicate_memberships", [])) for _, _, s, _ in fp_cases]
    fn_dups = [len(s.get("duplicate_memberships", [])) for _, _, s, _ in fn_keep + fn_review]
    tn_dups = [len(s.get("duplicate_memberships", [])) for _, _, s, _ in tn_cases]
    
    print(f"  TP dup_count: mean={statistics.mean(tp_dups):.1f}, median={statistics.median(tp_dups):.0f}")
    print(f"  FP dup_count: mean={statistics.mean(fp_dups):.1f}, median={statistics.median(fp_dups):.0f}")
    print(f"  FN dup_count: mean={statistics.mean(fn_dups):.1f}, median={statistics.median(fn_dups):.0f}")
    print(f"  TN dup_count: mean={statistics.mean(tn_dups):.1f}, median={statistics.median(tn_dups):.0f}")

    # Dimension 7: What do the justifications say?
    print(f"\n{'='*100}")
    print("DIMENSION 7: Sample TP vs FP justifications")
    print(f"{'='*100}")
    print(f"\n--- TRUE POSITIVES (correct discards) ---")
    for rid, c, s, a in tp_cases[:5]:
        print(f"\n  {rid} | signals={list(c['signals'])[:4]} | supplier={s.get('supplier','?')} | risk={s.get('supplier_risk_level','?')}")
        print(f"  Agent: {a['just'][:250]}")
    
    print(f"\n--- FALSE POSITIVES (wrong discards) ---")
    for rid, c, s, a in fp_cases[:5]:
        print(f"\n  {rid} | signals={list(c['signals'])[:4]} | supplier={s.get('supplier','?')} | risk={s.get('supplier_risk_level','?')}")
        print(f"  Agent: {a['just'][:250]}")

    # Key question: what distinguishes TP from FP?
    print(f"\n{'='*100}")
    print("KEY DISTINGUISHERS: TP vs FP")
    print(f"{'='*100}")
    
    # Check: do TP cases have more high-precision signals?
    high_prec = {"long_low_specificity_text", "termflags_nonzero", "ai_or_overpolished_text_marker", "generic_placeholder_open_end", "pasted_text_flag"}
    tp_hp = sum(1 for _, c, _, _ in tp_cases if c["signals"] & high_prec)
    fp_hp = sum(1 for _, c, _, _ in fp_cases if c["signals"] & high_prec)
    print(f"\n  High-precision signal present:")
    print(f"    TP: {tp_hp}/{len(tp_cases)} ({tp_hp/len(tp_cases)*100:.1f}%)")
    print(f"    FP: {fp_hp}/{len(fp_cases)} ({fp_hp/len(fp_cases)*100:.1f}%)")
    
    # Check: do TP cases have faster timing?
    tp_fast = sum(1 for _, _, s, _ in tp_cases if s.get("timing_percentile") in ("bottom_10", "bottom_25"))
    fp_fast = sum(1 for _, _, s, _ in fp_cases if s.get("timing_percentile") in ("bottom_10", "bottom_25"))
    print(f"\n  Fast timing (bottom 25%):")
    print(f"    TP: {tp_fast}/{len(tp_cases)} ({tp_fast/len(tp_cases)*100:.1f}%)")
    print(f"    FP: {fp_fast}/{len(fp_cases)} ({fp_fast/len(fp_cases)*100:.1f}%)")
    
    # Check: do TP cases have more duplicate memberships?
    tp_many_dups = sum(1 for _, _, s, _ in tp_cases if len(s.get("duplicate_memberships", [])) >= 3)
    fp_many_dups = sum(1 for _, _, s, _ in fp_cases if len(s.get("duplicate_memberships", [])) >= 3)
    print(f"\n  3+ duplicate text memberships:")
    print(f"    TP: {tp_many_dups}/{len(tp_cases)} ({tp_many_dups/len(tp_cases)*100:.1f}%)")
    print(f"    FP: {fp_many_dups}/{len(fp_cases)} ({fp_many_dups/len(fp_cases)*100:.1f}%)")
    
    # Check: supplier reject rate
    tp_srr = [s.get("supplier_reject_rate", 0) for _, _, s, _ in tp_cases]
    fp_srr = [s.get("supplier_reject_rate", 0) for _, _, s, _ in fp_cases]
    print(f"\n  Supplier reject rate:")
    print(f"    TP: mean={statistics.mean(tp_srr):.1f}%")
    print(f"    FP: mean={statistics.mean(fp_srr):.1f}%")

    # What if we only discarded cases with high-precision signals OR very fast timing OR high supplier risk?
    print(f"\n{'='*100}")
    print("REFINED RULE SIMULATION")
    print(f"{'='*100}")
    
    # Rule A: Only discard if high-precision signal present
    tp_a = sum(1 for _, c, _, _ in tp_cases if c["signals"] & high_prec)
    fp_a = sum(1 for _, c, s, _ in tp_cases + fp_cases if c["signals"] & high_prec and c["status"] == 3)
    tp_a2 = sum(1 for _, c, _, _ in tp_cases if c["signals"] & high_prec)
    fp_a2 = sum(1 for _, c, _, _ in fp_cases if c["signals"] & high_prec)
    print(f"\n  Rule A: Only discard if high-precision signal present")
    print(f"    TP: {tp_a2}, FP: {fp_a2}, Precision: {tp_a2/(tp_a2+fp_a2)*100:.1f}%" if (tp_a2+fp_a2) > 0 else "    No cases")
    
    # Rule B: Discard if (high-precision signal) OR (supplier=high AND 3+ signals)
    def rule_b(c, s):
        return (c["signals"] & high_prec) or (s.get("supplier_risk_level") == "high" and c["signal_count"] >= 3)
    tp_b = sum(1 for _, c, s, _ in tp_cases if rule_b(c, s))
    fp_b = sum(1 for _, c, s, _ in fp_cases if rule_b(c, s))
    print(f"\n  Rule B: Discard if (high-precision signal) OR (supplier=high AND 3+ signals)")
    print(f"    TP: {tp_b}, FP: {fp_b}, Precision: {tp_b/(tp_b+fp_b)*100:.1f}%" if (tp_b+fp_b) > 0 else "    No cases")
    
    # Rule C: Discard if (high-precision signal) OR (fast timing AND 3+ signals) OR (supplier=high AND 4+ signals)
    def rule_c(c, s):
        return ((c["signals"] & high_prec) or 
                (s.get("timing_percentile") in ("bottom_10", "bottom_25") and c["signal_count"] >= 3) or
                (s.get("supplier_risk_level") == "high" and c["signal_count"] >= 4))
    tp_c = sum(1 for _, c, s, _ in tp_cases if rule_c(c, s))
    fp_c = sum(1 for _, c, s, _ in fp_cases if rule_c(c, s))
    print(f"\n  Rule C: Discard if (high-precision) OR (fast AND 3+ sigs) OR (high supplier AND 4+ sigs)")
    print(f"    TP: {tp_c}, FP: {fp_c}, Precision: {tp_c/(tp_c+fp_c)*100:.1f}%" if (tp_c+fp_c) > 0 else "    No cases")


if __name__ == "__main__":
    main()
