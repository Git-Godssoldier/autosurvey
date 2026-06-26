#!/usr/bin/env python3
"""Deep analysis of signal combinations to find path to 20% discard at >90% accuracy."""

import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from itertools import combinations

SIGNAL_MAP = "/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/status-ground-truth-calibration/core_loop_2026-06-24/status_respondent_signal_map.csv"

def load_client_data():
    """Load all client annotations with signals."""
    records = []
    with open(SIGNAL_MAP) as f:
        reader = csv.DictReader(f)
        for row in reader:
            signals = set(row["signals"].split("; ") if row["signals"] else [])
            records.append({
                "dataset": row["dataset"],
                "respondent_key": row["respondent_key"],
                "status": int(row["status"]),
                "decision": row["tfg_decision"],
                "signals": signals,
                "signal_count": int(row["signal_count"]),
            })
    return records

def main():
    records = load_client_data()
    total = len(records)
    rejects = [r for r in records if r["status"] == 5]
    accepts = [r for r in records if r["status"] == 3]
    
    print(f"Total: {total}, Rejects: {len(rejects)} ({len(rejects)/total*100:.1f}%), Accepts: {len(accepts)} ({len(accepts)/total*100:.1f}%)")
    
    # 1. Signal frequency in rejects vs accepts
    reject_signals = Counter()
    accept_signals = Counter()
    for r in rejects:
        for s in r["signals"]:
            reject_signals[s] += 1
    for r in accepts:
        for s in r["signals"]:
            accept_signals[s] += 1
    
    print(f"\n{'='*100}")
    print("SIGNAL-LEVEL ANALYSIS: Reject vs Accept rates")
    print(f"{'='*100}")
    print(f"\n{'Signal':<50} {'Rej':>6} {'Acc':>6} {'Rej%':>6} {'Acc%':>6} {'Lift':>6} {'Prec':>6}")
    print(f"{'-'*50} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*6} {'-'*6}")
    
    all_signals = set(reject_signals.keys()) | set(accept_signals.keys())
    signal_stats = []
    for s in all_signals:
        rej = reject_signals.get(s, 0)
        acc = accept_signals.get(s, 0)
        rej_rate = rej / len(rejects) * 100
        acc_rate = acc / len(accepts) * 100
        lift = rej_rate / acc_rate if acc_rate > 0 else float('inf')
        prec = rej / (rej + acc) * 100 if (rej + acc) > 0 else 0
        signal_stats.append((s, rej, acc, rej_rate, acc_rate, lift, prec))
    
    # Sort by precision (most predictive first)
    signal_stats.sort(key=lambda x: (x[6], x[1]), reverse=True)
    for s, rej, acc, rr, ar, lift, prec in signal_stats[:40]:
        print(f"{s:<50} {rej:>6} {acc:>6} {rr:>5.1f}% {ar:>5.1f}% {lift:>5.1f}x {prec:>5.1f}%")
    
    # 2. Signal count analysis
    print(f"\n{'='*100}")
    print("SIGNAL COUNT ANALYSIS: How many signals do rejects vs accepts have?")
    print(f"{'='*100}")
    rej_counts = Counter(r["signal_count"] for r in rejects)
    acc_counts = Counter(r["signal_count"] for r in accepts)
    print(f"\n{'Signal Count':>12} {'Rejects':>8} {'Accepts':>8} {'Reject%':>8} {'Precision':>10}")
    for sc in sorted(set(rej_counts.keys()) | set(acc_counts.keys())):
        rj = rej_counts.get(sc, 0)
        ac = acc_counts.get(sc, 0)
        rej_pct = rj / len(rejects) * 100
        prec = rj / (rj + ac) * 100 if (rj + ac) > 0 else 0
        print(f"{sc:>12} {rj:>8} {ac:>8} {rej_pct:>7.1f}% {prec:>9.1f}%")
    
    # 3. Find the optimal signal count threshold
    print(f"\n{'='*100}")
    print("THRESHOLD ANALYSIS: Discard if signal_count >= N")
    print(f"{'='*100}")
    print(f"\n{'Threshold':>10} {'Discard':>8} {'Rate':>6} {'TP':>6} {'FP':>6} {'Prec':>6} {'Recall':>7} {'Acc':>6}")
    for threshold in range(1, 15):
        tp = sum(1 for r in rejects if r["signal_count"] >= threshold)
        fp = sum(1 for r in accepts if r["signal_count"] >= threshold)
        discards = tp + fp
        rate = discards / total * 100
        prec = tp / discards * 100 if discards > 0 else 0
        recall = tp / len(rejects) * 100
        acc = (tp + (len(accepts) - fp)) / total * 100
        print(f"{threshold:>10} {discards:>8} {rate:>5.1f}% {tp:>6} {fp:>6} {prec:>5.1f}% {recall:>6.1f}% {acc:>5.1f}%")
    
    # 4. Key signal combination analysis
    print(f"\n{'='*100}")
    print("KEY SIGNAL COMBINATIONS: Which pairs are most predictive?")
    print(f"{'='*100}")
    
    # Focus on the most common signals
    top_signals = [s for s, _, _, _, _, _, _ in signal_stats if _ >= 100][:15]
    
    combo_stats = []
    for s1, s2 in combinations(top_signals, 2):
        rej_both = sum(1 for r in rejects if s1 in r["signals"] and s2 in r["signals"])
        acc_both = sum(1 for r in accepts if s1 in r["signals"] and s2 in r["signals"])
        if rej_both + acc_both < 50:
            continue
        prec = rej_both / (rej_both + acc_both) * 100 if (rej_both + acc_both) > 0 else 0
        combo_stats.append((f"{s1} + {s2}", rej_both, acc_both, prec))
    
    combo_stats.sort(key=lambda x: (x[3], x[1]), reverse=True)
    print(f"\n{'Combination':<80} {'Rej':>6} {'Acc':>6} {'Prec':>6}")
    for combo, rej, acc, prec in combo_stats[:20]:
        print(f"{combo:<80} {rej:>6} {acc:>6} {prec:>5.1f}%")
    
    # 5. What signals do rejects have that accepts DON'T have?
    print(f"\n{'='*100}")
    print("SIGNALS UNIQUE TO REJECTS (high reject rate, low accept rate)")
    print(f"{'='*100}")
    unique_reject_signals = []
    for s, rej, acc, rr, ar, lift, prec in signal_stats:
        if rej >= 10 and acc <= 5:
            unique_reject_signals.append((s, rej, acc, prec, lift))
    unique_reject_signals.sort(key=lambda x: x[1], reverse=True)
    for s, rej, acc, prec, lift in unique_reject_signals[:20]:
        print(f"  {s:<50} rej={rej:>4} acc={acc:>3} prec={prec:.1f}% lift={lift:.1f}x")
    
    # 6. Per-dataset reject rates
    print(f"\n{'='*100}")
    print("PER-DATASET REJECT RATES")
    print(f"{'='*100}")
    ds_stats = defaultdict(lambda: {"total": 0, "reject": 0, "accept": 0})
    for r in records:
        ds_stats[r["dataset"]]["total"] += 1
        if r["status"] == 5:
            ds_stats[r["dataset"]]["reject"] += 1
        else:
            ds_stats[r["dataset"]]["accept"] += 1
    
    print(f"\n{'Dataset':<50} {'Total':>7} {'Reject':>7} {'Accept':>7} {'Rej%':>6}")
    for ds in sorted(ds_stats.keys()):
        s = ds_stats[ds]
        print(f"{ds:<50} {s['total']:>7} {s['reject']:>7} {s['accept']:>7} {s['reject']/s['total']*100:>5.1f}%")
    
    # 7. Simulate: discard if signal_count >= N AND specific high-precision signals present
    print(f"\n{'='*100}")
    print("COMBINED RULE: signal_count >= N OR has high-precision signal")
    print(f"{'='*100}")
    
    # High-precision signals (prec > 60% with at least 20 cases)
    high_prec_signals = [s for s, rej, acc, _, _, _, prec in signal_stats if prec > 60 and rej >= 20]
    print(f"\nHigh-precision signals (prec>60%, rej>=20): {high_prec_signals}")
    
    print(f"\n{'Rule':<60} {'Disc':>6} {'Rate':>6} {'TP':>6} {'FP':>6} {'Prec':>6} {'Rec':>7} {'Acc':>6}")
    for threshold in range(3, 12):
        for hp_signal in high_prec_signals[:5]:
            tp = sum(1 for r in rejects if r["signal_count"] >= threshold or hp_signal in r["signals"])
            fp = sum(1 for r in accepts if r["signal_count"] >= threshold or hp_signal in r["signals"])
            discards = tp + fp
            rate = discards / total * 100
            prec = tp / discards * 100 if discards > 0 else 0
            recall = tp / len(rejects) * 100
            acc = (tp + (len(accepts) - fp)) / total * 100
            rule = f"count>={threshold} OR {hp_signal[:30]}"
            print(f"{rule:<60} {discards:>6} {rate:>5.1f}% {tp:>6} {fp:>6} {prec:>5.1f}% {recall:>6.1f}% {acc:>5.1f}%")
    
    # 8. The real question: what does the client's decision look like?
    # Let's check if signal_count alone is the decision rule
    print(f"\n{'='*100}")
    print("CLIENT DECISION REVERSE ENGINEERING")
    print(f"{'='*100}")
    
    # Check: is there a simple threshold on signal_count that matches client decisions?
    best_match = 0
    best_threshold = 0
    for threshold in range(1, 20):
        matches = sum(1 for r in records if (r["signal_count"] >= threshold) == (r["status"] == 5))
        if matches > best_match:
            best_match = matches
            best_threshold = threshold
    print(f"\nBest signal_count threshold: >= {best_threshold} (matches {best_match}/{total} = {best_match/total*100:.1f}%)")
    
    # Check specific signal presence
    # What % of rejects have 0 signals?
    zero_signal_rejects = sum(1 for r in rejects if r["signal_count"] == 0)
    zero_signal_accepts = sum(1 for r in accepts if r["signal_count"] == 0)
    print(f"\nRejects with 0 signals: {zero_signal_rejects} ({zero_signal_rejects/len(rejects)*100:.1f}%)")
    print(f"Accepts with 0 signals: {zero_signal_accepts} ({zero_signal_accepts/len(accepts)*100:.1f}%)")
    
    # What's the signal count distribution for rejects vs accepts?
    print(f"\nSignal count distribution:")
    print(f"  Rejects: mean={sum(r['signal_count'] for r in rejects)/len(rejects):.1f}, median={sorted(r['signal_count'] for r in rejects)[len(rejects)//2]}")
    print(f"  Accepts: mean={sum(r['signal_count'] for r in accepts)/len(accepts):.1f}, median={sorted(r['signal_count'] for r in accepts)[len(accepts)//2]}")


if __name__ == "__main__":
    main()
