#!/usr/bin/env python3
"""Extract best examples of true positives, false positives, true negatives, and false negatives
from the Delta v2 run to build an examples library for the skill."""

import json
import csv
from pathlib import Path
from collections import defaultdict

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
                    "tfg_decision": row["tfg_decision"],
                    "signals": row["signals"],
                    "signal_count": int(row["signal_count"]),
                }

    # Load staged packets
    staged = {}
    with open(STAGED) as f:
        for line in f:
            if line.strip():
                p = json.loads(line)
                # Normalize qtime field
                if "qtime_seconds" in p and "qtime" not in p:
                    p["qtime"] = p["qtime_seconds"]
                staged[p["respondent_id"]] = p

    # Load V2 determinations
    v2 = {}
    for f in sorted((V2_DIR / "final_determinations").glob("*.ndjson")):
        with open(f) as fh:
            for line in fh:
                if line.strip():
                    d = json.loads(line)
                    rid = d.get("respondent_id") or d.get("id")
                    v2[rid] = d

    # Classify each respondent
    tp = []  # True positives: agent discarded, client rejected
    fp = []  # False positives: agent discarded, client kept
    tn = []  # True negatives: agent kept, client kept
    fn_keep = []  # False negatives: agent kept, client rejected
    fn_review = []  # False negatives: agent reviewed, client rejected

    for rid, c in client.items():
        if rid not in v2 or rid not in staged:
            continue
        agent_det = get_det(v2[rid])
        client_rejected = c["tfg_decision"] == "rejected"
        s = staged[rid]
        just = v2[rid].get("justification", "")

        entry = {
            "respondent_id": rid,
            "client_signals": c["signals"],
            "signal_count": c["signal_count"],
            "supplier": s.get("supplier", "Unknown"),
            "supplier_risk_level": s.get("supplier_risk_level", "unknown"),
            "supplier_reject_rate": s.get("supplier_reject_rate", 0),
            "qtime": s.get("qtime", 0),
            "timing_percentile": s.get("timing_percentile", "unknown"),
            "duplicate_memberships": s.get("duplicate_memberships", 0),
            "agent_determination": agent_det,
            "client_status": c["tfg_decision"],
            "justification": just[:500],
            "answer_chain": s.get("answer_chain", {}),
        }

        if agent_det == "discard" and client_rejected:
            tp.append(entry)
        elif agent_det == "discard" and not client_rejected:
            fp.append(entry)
        elif agent_det == "keep" and not client_rejected:
            tn.append(entry)
        elif agent_det == "keep" and client_rejected:
            fn_keep.append(entry)
        elif agent_det == "review" and client_rejected:
            fn_review.append(entry)

    # Extract answer chain summaries for examples
    def summarize_chain(entry):
        chain = entry.get("answer_chain", [])
        if not chain:
            return "(no answer chain)"
        parts = []
        if isinstance(chain, list):
            for item in chain[:15]:
                field = item.get("field", "?")
                qtext = item.get("question_text", "")[:80]
                label = item.get("label", item.get("raw_value", ""))
                a_str = str(label)
                if len(a_str) > 200:
                    a_str = a_str[:200] + "..."
                parts.append(f"  {field} [{qtext}]: {a_str}")
        elif isinstance(chain, dict):
            for q, a in list(chain.items())[:15]:
                a_str = str(a)
                if len(a_str) > 200:
                    a_str = a_str[:200] + "..."
                parts.append(f"  {q}: {a_str}")
        return "\n".join(parts)

    # Select best examples
    # TPs: ones with clear TIER 1 signals or clear incoherence
    tp_best = sorted(tp, key=lambda x: (
        "termflags_nonzero" in x["client_signals"],
        "ai_or_overpolished" in x["client_signals"],
        "generic_placeholder" in x["client_signals"],
        x["supplier_risk_level"] == "high",
    ), reverse=True)[:8]

    # FPs: ones where the agent was too aggressive
    fp_best = sorted(fp, key=lambda x: (
        x["supplier_risk_level"] == "moderate",
        "matrix_near_straightline" in x["client_signals"],
        x["timing_percentile"] in ("bottom_10", "bottom_25"),
    ), reverse=True)[:8]

    # TNs: correctly kept, high signal count but coherent
    tn_best = sorted(tn, key=lambda x: x["signal_count"], reverse=True)[:8]

    # FNs: missed by agent (kept but should have been discarded)
    fn_best = sorted(fn_keep, key=lambda x: x["signal_count"], reverse=True)[:8]

    # Print examples
    print("=" * 80)
    print("TRUE POSITIVES (Correctly Discarded)")
    print("=" * 80)
    for e in tp_best:
        print(f"\n--- {e['respondent_id']} ---")
        print(f"Signals: {e['client_signals']}")
        print(f"Supplier: {e['supplier']} ({e['supplier_risk_level']}, {e['supplier_reject_rate']}%)")
        print(f"Timing: {e['qtime']}s ({e['timing_percentile']})")
        print(f"Agent: {e['agent_determination']}, Client: {e['client_status']}")
        print(f"Justification: {e['justification'][:300]}")
        print(f"Answer chain (first 15 questions):")
        print(summarize_chain(e))

    print("\n" + "=" * 80)
    print("FALSE POSITIVES (Wrongly Discarded — Client Kept)")
    print("=" * 80)
    for e in fp_best:
        print(f"\n--- {e['respondent_id']} ---")
        print(f"Signals: {e['client_signals']}")
        print(f"Supplier: {e['supplier']} ({e['supplier_risk_level']}, {e['supplier_reject_rate']}%)")
        print(f"Timing: {e['qtime']}s ({e['timing_percentile']})")
        print(f"Agent: {e['agent_determination']}, Client: {e['client_status']}")
        print(f"Justification: {e['justification'][:300]}")
        print(f"Answer chain (first 15 questions):")
        print(summarize_chain(e))

    print("\n" + "=" * 80)
    print("TRUE NEGATIVES (Correctly Kept — High Signal Count but Authentic)")
    print("=" * 80)
    for e in tn_best:
        print(f"\n--- {e['respondent_id']} ---")
        print(f"Signals: {e['client_signals']}")
        print(f"Supplier: {e['supplier']} ({e['supplier_risk_level']}, {e['supplier_reject_rate']}%)")
        print(f"Timing: {e['qtime']}s ({e['timing_percentile']})")
        print(f"Agent: {e['agent_determination']}, Client: {e['client_status']}")
        print(f"Justification: {e['justification'][:300]}")
        print(f"Answer chain (first 15 questions):")
        print(summarize_chain(e))

    print("\n" + "=" * 80)
    print("FALSE NEGATIVES (Missed — Agent Kept but Client Rejected)")
    print("=" * 80)
    for e in fn_best:
        print(f"\n--- {e['respondent_id']} ---")
        print(f"Signals: {e['client_signals']}")
        print(f"Supplier: {e['supplier']} ({e['supplier_risk_level']}, {e['supplier_reject_rate']}%)")
        print(f"Timing: {e['qtime']}s ({e['timing_percentile']})")
        print(f"Agent: {e['agent_determination']}, Client: {e['client_status']}")
        print(f"Justification: {e['justification'][:300]}")
        print(f"Answer chain (first 15 questions):")
        print(summarize_chain(e))

    # Summary stats
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"TP (correct discards): {len(tp)}")
    print(f"FP (wrong discards): {len(fp)}")
    print(f"TN (correct keeps): {len(tn)}")
    print(f"FN-keep (missed, kept): {len(fn_keep)}")
    print(f"FN-review (missed, reviewed): {len(fn_review)}")
    precision = len(tp) / (len(tp) + len(fp)) if (len(tp) + len(fp)) > 0 else 0
    recall = len(tp) / (len(tp) + len(fn_keep) + len(fn_review)) if (len(tp) + len(fn_keep) + len(fn_review)) > 0 else 0
    print(f"Precision: {precision:.1%}")
    print(f"Recall: {recall:.1%}")

if __name__ == "__main__":
    main()
