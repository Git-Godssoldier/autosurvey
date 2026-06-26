#!/usr/bin/env python3
"""Deep dive: What semantic patterns distinguish client rejects from accepts that the agent is missing?"""

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

SIGNAL_MAP = "/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/status-ground-truth-calibration/core_loop_2026-06-24/status_respondent_signal_map.csv"
BLIND_BASE = Path("/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/blind-runs-agent")

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

def get_determination(record):
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

def load_agent_dets(ds_dir):
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
                            "det": get_determination(r),
                            "just": r.get("justification", "")[:300],
                        }
                except:
                    continue
    return records

def main():
    # Load client data
    client = {}
    with open(SIGNAL_MAP) as f:
        for row in csv.DictReader(f):
            client[row["respondent_key"]] = {
                "dataset": row["dataset"],
                "status": int(row["status"]),
                "signals": set(row["signals"].split("; ") if row["signals"] else []),
                "signal_count": int(row["signal_count"]),
            }
    
    # Load all agent determinations
    agent = {}
    for client_ds, blind_ds in DATASET_MAP.items():
        blind_dir = BLIND_BASE / blind_ds
        dets = load_agent_dets(blind_dir)
        for rid, det in dets.items():
            agent[rid] = {**det, "dataset": blind_ds}
    
    # Match
    matched = [(rid, client[rid], agent[rid]) for rid in client if rid in agent]
    print(f"Matched: {len(matched)}/{len(client)}")
    
    # Per-dataset: what's the agent's discard rate vs client reject rate?
    print(f"\n{'='*130}")
    print("PER-DATASET CALIBRATION ANALYSIS")
    print(f"{'='*130}")
    print(f"\n{'Dataset':<45} {'Client%':>7} {'Agent%':>7} {'Gap':>7} {'Agent Prec':>10} {'Agent Recall':>12} {'Needed':>7}")
    
    ds_groups = defaultdict(lambda: {"total": 0, "client_rej": 0, "agent_disc": 0, "tp": 0, "fp": 0, "fn": 0})
    for rid, c, a in matched:
        ds = a["dataset"]
        ds_groups[ds]["total"] += 1
        if c["status"] == 5:
            ds_groups[ds]["client_rej"] += 1
        if a["det"] == "discard":
            ds_groups[ds]["agent_disc"] += 1
            if c["status"] == 5:
                ds_groups[ds]["tp"] += 1
            else:
                ds_groups[ds]["fp"] += 1
        elif c["status"] == 5:
            ds_groups[ds]["fn"] += 1
    
    for ds in sorted(ds_groups.keys()):
        s = ds_groups[ds]
        client_rate = s["client_rej"] / s["total"] * 100
        agent_rate = s["agent_disc"] / s["total"] * 100
        gap = client_rate - agent_rate
        prec = s["tp"] / s["agent_disc"] * 100 if s["agent_disc"] > 0 else 0
        recall = s["tp"] / s["client_rej"] * 100 if s["client_rej"] > 0 else 0
        # How many more discards needed to match 20% rate
        target = int(s["total"] * 0.20)
        needed = max(0, target - s["agent_disc"])
        print(f"{ds:<45} {client_rate:>6.1f}% {agent_rate:>6.1f}% {gap:>6.1f}% {prec:>9.1f}% {recall:>11.1f}% {needed:>7}")
    
    # Analyze: What do false negative KEEP cases look like?
    # These are client rejects that the agent confidently kept
    print(f"\n{'='*130}")
    print("ANALYSIS: Client rejects that agent KEPT (most concerning false negatives)")
    print(f"{'='*130}")
    
    fn_keep = [(rid, c, a) for rid, c, a in matched if c["status"] == 5 and a["det"] == "keep"]
    
    # What signals do these have?
    fn_keep_signals = Counter()
    for rid, c, a in fn_keep:
        for s in c["signals"]:
            fn_keep_signals[s] += 1
    
    print(f"\nTotal FN-keep: {len(fn_keep)}")
    print(f"\nTop signals in FN-keep cases:")
    for sig, cnt in fn_keep_signals.most_common(20):
        print(f"  {sig}: {cnt} ({cnt/len(fn_keep)*100:.1f}%)")
    
    # Per-dataset FN-keep distribution
    fn_keep_ds = Counter(a["dataset"] for _, _, a in fn_keep)
    print(f"\nFN-keep by dataset:")
    for ds, cnt in fn_keep_ds.most_common():
        total_rej = ds_groups[ds]["client_rej"]
        print(f"  {ds}: {cnt}/{total_rej} rejects kept ({cnt/total_rej*100:.1f}%)")
    
    # Sample FN-keep justifications
    print(f"\nSample FN-keep justifications (first 10):")
    for rid, c, a in fn_keep[:10]:
        print(f"\n  {rid} [{a['dataset']}]")
        print(f"  Signals: {', '.join(list(c['signals'])[:5])}")
        print(f"  Agent said: {a['just'][:200]}")
    
    # Analyze: What do false negative REVIEW cases look like?
    print(f"\n{'='*130}")
    print("ANALYSIS: Client rejects that agent REVIEWED (borderline cases)")
    print(f"{'='*130}")
    
    fn_review = [(rid, c, a) for rid, c, a in matched if c["status"] == 5 and a["det"] == "review"]
    print(f"\nTotal FN-review: {len(fn_review)}")
    
    # What signals distinguish review-rejects from review-accepts?
    review_reject_sigs = Counter()
    review_accept_sigs = Counter()
    for rid, c, a in matched:
        if a["det"] == "review":
            if c["status"] == 5:
                for s in c["signals"]:
                    review_reject_sigs[s] += 1
            else:
                for s in c["signals"]:
                    review_accept_sigs[s] += 1
    
    print(f"\nSignal enrichment in review-rejects vs review-accepts:")
    print(f"{'Signal':<50} {'RevRej':>7} {'RevAcc':>7} {'Enrich':>7}")
    all_sigs = set(review_reject_sigs.keys()) | set(review_accept_sigs.keys())
    enrichments = []
    for s in all_sigs:
        rr = review_reject_sigs.get(s, 0)
        ra = review_accept_sigs.get(s, 0)
        if rr + ra < 20:
            continue
        rr_rate = rr / len(fn_review) * 100
        ra_rate = ra / (sum(1 for _, c, a in matched if a["det"] == "review" and c["status"] == 3)) * 100
        enrich = rr_rate / ra_rate if ra_rate > 0 else float('inf')
        enrichments.append((s, rr, ra, enrich))
    
    enrichments.sort(key=lambda x: x[3], reverse=True)
    for s, rr, ra, enrich in enrichments[:20]:
        print(f"  {s:<50} {rr:>7} {ra:>7} {enrich:>6.2f}x")
    
    # THE KEY QUESTION: What would get us to 20% discard at >90% accuracy?
    print(f"\n{'='*130}")
    print("STRATEGY ANALYSIS: How to reach 20% discard at >90% accuracy")
    print(f"{'='*130}")
    
    total = len(matched)
    total_rejects = sum(1 for _, c, _ in matched if c["status"] == 5)
    total_accepts = total - total_rejects
    
    # Current state
    current_tp = sum(1 for _, c, a in matched if c["status"] == 5 and a["det"] == "discard")
    current_fp = sum(1 for _, c, a in matched if c["status"] == 3 and a["det"] == "discard")
    current_disc = current_tp + current_fp
    
    print(f"\nCurrent: {current_disc} discards ({current_disc/total*100:.1f}%), {current_tp} TP, {current_fp} FP")
    print(f"  Precision: {current_tp/current_disc*100:.1f}%, Recall: {current_tp/total_rejects*100:.1f}%, Accuracy: {(current_tp + total_accepts - current_fp)/total*100:.1f}%")
    
    # Target: 20% discard, >90% accuracy
    target_disc = int(total * 0.20)
    max_fp = int(target_disc * 0.10)  # 10% FP = 90% accuracy
    min_tp = target_disc - max_fp
    
    print(f"\nTarget: {target_disc} discards (20.0%), max {max_fp} FP, min {min_tp} TP")
    print(f"  Required precision: {min_tp/target_disc*100:.1f}%")
    print(f"  Required recall: {min_tp/total_rejects*100:.1f}%")
    
    # Strategy 1: Per-dataset calibration
    # If we set discard rate = client reject rate per dataset, what happens?
    print(f"\n--- Strategy 1: Match client reject rate per dataset ---")
    # Sort respondents by agent confidence within each dataset
    # For now, simulate: if we discarded at the client's reject rate, what precision would we need?
    for ds in sorted(ds_groups.keys()):
        s = ds_groups[ds]
        target_ds = int(s["total"] * s["client_rej"] / s["total"])
        print(f"  {ds}: target {s['client_rej']} discards, currently {s['agent_disc']} (gap: {s['client_rej'] - s['agent_disc']})")
    
    # Strategy 2: Convert review→discard with signal-based filtering
    # Use high-enrichment signals to selectively convert reviews
    print(f"\n--- Strategy 2: Convert review→discard only when high-enrichment signals present ---")
    
    high_enrich_signals = [s for s, rr, ra, enrich in enrichments if enrich >= 1.5 and rr >= 20]
    print(f"  High-enrichment signals (>=1.5x, >=20 cases): {high_enrich_signals}")
    
    # Simulate: discard if (currently discard) OR (currently review AND has high-enrichment signal)
    new_tp = current_tp
    new_fp = current_fp
    converted = 0
    for rid, c, a in matched:
        if a["det"] == "review" and c["status"] == 5:
            if any(s in c["signals"] for s in high_enrich_signals):
                new_tp += 1
                converted += 1
        elif a["det"] == "review" and c["status"] == 3:
            if any(s in c["signals"] for s in high_enrich_signals):
                new_fp += 1
    
    new_disc = new_tp + new_fp
    new_prec = new_tp / new_disc * 100 if new_disc > 0 else 0
    new_recall = new_tp / total_rejects * 100
    new_acc = (new_tp + total_accepts - new_fp) / total * 100
    
    print(f"  Result: {new_disc} discards ({new_disc/total*100:.1f}%), {new_tp} TP, {new_fp} FP")
    print(f"  Precision: {new_prec:.1f}%, Recall: {new_recall:.1f}%, Accuracy: {new_acc:.1f}%")
    print(f"  Converted {converted} review-rejects to discards")
    
    # Strategy 3: Per-dataset supplier-level rejection
    # If a supplier has >X% reject rate, discard all from that supplier
    print(f"\n--- Strategy 3: Supplier-level rejection patterns ---")
    # We'd need supplier data from the staged packets
    # For now, just note this as a strategy
    
    # Strategy 4: Signal count + specific signal combination
    print(f"\n--- Strategy 4: Multi-signal scoring ---")
    # Assign weights to signals based on enrichment, then threshold
    # Signal weight = log(enrichment)
    import math
    signal_weights = {}
    for s, rr, ra, enrich in enrichments:
        signal_weights[s] = math.log(max(enrich, 1.0))
    
    # Score each respondent
    scores = []
    for rid, c, a in matched:
        score = sum(signal_weights.get(s, 0) for s in c["signals"])
        scores.append((score, c["status"], a["det"], rid))
    
    # Sort by score descending
    scores.sort(key=lambda x: x[0], reverse=True)
    
    # Find threshold that gives 20% discard at max accuracy
    print(f"\n  Score-based threshold simulation:")
    print(f"  {'Threshold':>10} {'Discard':>8} {'Rate':>6} {'TP':>6} {'FP':>6} {'Prec':>6} {'Recall':>7} {'Acc':>6}")
    for threshold_pct in [5, 10, 15, 20, 25, 30, 35, 40, 45, 50]:
        threshold_idx = int(total * threshold_pct / 100)
        threshold_score = scores[threshold_idx][0] if threshold_idx < len(scores) else 0
        tp = sum(1 for s, status, _, _ in scores[:threshold_idx] if status == 5)
        fp = sum(1 for s, status, _, _ in scores[:threshold_idx] if status == 3)
        disc = tp + fp
        prec = tp / disc * 100 if disc > 0 else 0
        recall = tp / total_rejects * 100
        acc = (tp + total_accepts - fp) / total * 100
        print(f"  {threshold_pct:>9}% {disc:>8} {disc/total*100:>5.1f}% {tp:>6} {fp:>6} {prec:>5.1f}% {recall:>6.1f}% {acc:>5.1f}%")
    
    # Strategy 5: Combine agent semantic + client signals
    print(f"\n--- Strategy 5: Agent discard OR (agent review + signal_score >= N) ---")
    print(f"  {'Signal Threshold':>18} {'Discard':>8} {'Rate':>6} {'TP':>6} {'FP':>6} {'Prec':>6} {'Recall':>7} {'Acc':>6}")
    for sig_threshold in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0]:
        tp = current_tp
        fp = current_fp
        for rid, c, a in matched:
            if a["det"] == "review":
                score = sum(signal_weights.get(s, 0) for s in c["signals"])
                if score >= sig_threshold:
                    if c["status"] == 5:
                        tp += 1
                    else:
                        fp += 1
        disc = tp + fp
        prec = tp / disc * 100 if disc > 0 else 0
        recall = tp / total_rejects * 100
        acc = (tp + total_accepts - fp) / total * 100
        print(f"  {sig_threshold:>17.1f} {disc:>8} {disc/total*100:>5.1f}% {tp:>6} {fp:>6} {prec:>5.1f}% {recall:>6.1f}% {acc:>5.1f}%")
    
    # Strategy 6: Agent discard OR (agent review + signal_count >= N)
    print(f"\n--- Strategy 6: Agent discard OR (agent review + signal_count >= N) ---")
    print(f"  {'Count Threshold':>17} {'Discard':>8} {'Rate':>6} {'TP':>6} {'FP':>6} {'Prec':>6} {'Recall':>7} {'Acc':>6}")
    for count_threshold in [3, 4, 5, 6, 7, 8]:
        tp = current_tp
        fp = current_fp
        for rid, c, a in matched:
            if a["det"] == "review" and c["signal_count"] >= count_threshold:
                if c["status"] == 5:
                    tp += 1
                else:
                    fp += 1
        disc = tp + fp
        prec = tp / disc * 100 if disc > 0 else 0
        recall = tp / total_rejects * 100
        acc = (tp + total_accepts - fp) / total * 100
        print(f"  {count_threshold:>17} {disc:>8} {disc/total*100:>5.1f}% {tp:>6} {fp:>6} {prec:>5.1f}% {recall:>6.1f}% {acc:>5.1f}%")


if __name__ == "__main__":
    main()
