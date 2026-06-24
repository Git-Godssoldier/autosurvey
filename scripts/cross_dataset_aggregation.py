#!/usr/bin/env python3
"""Cross-dataset pattern generalization analysis.

Reads all per-dataset proposition profiles and coherence analyses,
then computes generalized signal lift across all 11 datasets to identify
which patterns are universal vs dataset-specific.
"""
from __future__ import annotations

import json
import re
import statistics
from collections import Counter, defaultdict
from pathlib import Path

OUTPUT_BASE = Path("/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/cross-dataset-propositions")


def extract_open_text(prop: str) -> str:
    """Extract the quoted text from an open-text proposition."""
    m = re.search(r'"(.+)"', prop)
    return m.group(1) if m else ""


def classify_open_text(text: str) -> list[str]:
    """Classify an open-end text into signal categories."""
    signals = []
    tl = text.lower().strip()
    if not tl:
        return ["blank"]
    if len(tl) < 5:
        signals.append("very_short")
    if re.search(r"^none$|^n/?a$|^na$|^nothing$|^no$|^idk$|^i don.?t know$|^na\b", tl):
        signals.append("placeholder")
    if re.search(r"thank you|good survey|nice|amazing|love this|very good|great experience|very interesting|good brand", tl):
        signals.append("meta_praise")
    if re.search(r"the poll|the study|the survey examined|crucially|in order to determine|this research|this study|the (research|study) aimed", tl):
        signals.append("templated")
    if re.search(r"^[a-z]{20,}$|asdf|qwerty|bvnhgjut|fgggg", tl):
        signals.append("gibberish")
    if len(text.split()) > 40:
        signals.append("long_text_40plus")
    if len(text.split()) <= 3:
        signals.append("very_few_words_3less")
    if re.search(r"go to go to go to|was the one who was the one who|repeat repeat", tl):
        signals.append("repetition_loop")
    # Non-English detection (broad)
    if re.search(r"zła woda|badanie|filtrów|dotyczące|encuesta|examen|examinó|estudio|estudia|mémoire|sondage", tl):
        signals.append("non_english")
    return signals


def analyze_dataset(ds_name: str) -> dict:
    """Analyze a single dataset's proposition profiles for generalized signals."""
    ds_dir = OUTPUT_BASE / ds_name
    if not ds_dir.exists():
        return {"dataset": ds_name, "error": "not found"}

    t5 = [json.loads(l) for l in (ds_dir / "t5_self_claim_profiles.ndjson").read_text().splitlines()]
    t3 = [json.loads(l) for l in (ds_dir / "t3_guardrail_profiles.ndjson").read_text().splitlines()]

    # 1. Open-end text signal analysis
    t5_oe_signals = Counter()
    t3_oe_signals = Counter()
    t5_oe_texts = []
    t3_oe_texts = []

    for profile in t5:
        for prop in profile.get("self_claim_propositions", []):
            if prop["type"] == "open_text":
                text = extract_open_text(prop["proposition"])
                if text:
                    t5_oe_texts.append(text)
                    for sig in classify_open_text(text):
                        t5_oe_signals[sig] += 1

    for profile in t3:
        for prop in profile.get("self_claim_propositions", []):
            if prop["type"] == "open_text":
                text = extract_open_text(prop["proposition"])
                if text:
                    t3_oe_texts.append(text)
                    for sig in classify_open_text(text):
                        t3_oe_signals[sig] += 1

    # 2. Timing analysis
    t5_qt = [p["qtime_seconds"] for p in t5 if p["qtime_seconds"]]
    t3_qt = [p["qtime_seconds"] for p in t3 if p["qtime_seconds"]]
    t5_qt_med = statistics.median(t5_qt) if t5_qt else 0
    t3_qt_med = statistics.median(t3_qt) if t3_qt else 0
    t5_fast = sum(1 for q in t5_qt if q < 200) / len(t5_qt) if t5_qt else 0
    t3_fast = sum(1 for q in t3_qt if q < 200) / len(t3_qt) if t3_qt else 0

    # 3. Supplier analysis
    t5_no_sup = sum(1 for p in t5 if not p["supplier"] or str(p["supplier"]).strip() == "") / len(t5)
    t3_no_sup = sum(1 for p in t3 if not p["supplier"] or str(p["supplier"]).strip() == "") / len(t3)

    # 4. Proposition count analysis
    t5_prop_counts = [p["proposition_count"] for p in t5]
    t3_prop_counts = [p["proposition_count"] for p in t3]
    t5_low_prop = sum(1 for c in t5_prop_counts if c < 15) / len(t5_prop_counts) if t5_prop_counts else 0
    t3_low_prop = sum(1 for c in t3_prop_counts if c < 15) / len(t3_prop_counts) if t3_prop_counts else 0

    # 5. Compute lift for each open-end signal
    oe_lift = {}
    all_signals = set(list(t5_oe_signals.keys()) + list(t3_oe_signals.keys()))
    for sig in all_signals:
        t5_rate = t5_oe_signals.get(sig, 0) / max(len(t5_oe_texts), 1)
        t3_rate = t3_oe_signals.get(sig, 0) / max(len(t3_oe_texts), 1)
        oe_lift[sig] = {
            "t5_count": t5_oe_signals.get(sig, 0),
            "t3_count": t3_oe_signals.get(sig, 0),
            "t5_rate": round(t5_rate, 4),
            "t3_rate": round(t3_rate, 4),
            "lift": round(t5_rate / max(t3_rate, 0.001), 2),
        }

    return {
        "dataset": ds_name,
        "t5_total": len(t5),
        "t3_guardrail": len(t3),
        "t5_open_texts": len(t5_oe_texts),
        "t3_open_texts": len(t3_oe_texts),
        "open_end_signals": dict(oe_lift),
        "timing": {
            "t5_median": round(t5_qt_med, 1),
            "t3_median": round(t3_qt_med, 1),
            "t5_faster": t5_qt_med < t3_qt_med,
            "t5_fast_rate": round(t5_fast, 4),
            "t3_fast_rate": round(t3_fast, 4),
            "fast_lift": round(t5_fast / max(t3_fast, 0.001), 2),
        },
        "supplier": {
            "t5_missing_rate": round(t5_no_sup, 4),
            "t3_missing_rate": round(t3_no_sup, 4),
            "lift": round(t5_no_sup / max(t3_no_sup, 0.001), 2),
        },
        "proposition_count": {
            "t5_avg": round(statistics.mean(t5_prop_counts), 1) if t5_prop_counts else 0,
            "t3_avg": round(statistics.mean(t3_prop_counts), 1) if t3_prop_counts else 0,
            "t5_low_rate": round(t5_low_prop, 4),
            "t3_low_rate": round(t3_low_prop, 4),
        },
    }


def main():
    # Find all dataset directories
    datasets = sorted([d.name for d in OUTPUT_BASE.iterdir() if d.is_dir() and (d / "t5_self_claim_profiles.ndjson").exists()])

    results = []
    for ds in datasets:
        result = analyze_dataset(ds)
        results.append(result)

    # Aggregate: which signals appear with lift > 2x across multiple datasets?
    signal_lifts = defaultdict(list)  # signal -> [(dataset, lift)]
    for r in results:
        if "error" in r:
            continue
        for sig, data in r.get("open_end_signals", {}).items():
            signal_lifts[sig].append((r["dataset"], data["lift"], data["t5_rate"], data["t3_rate"]))

    # Timing patterns
    timing_patterns = []
    for r in results:
        if "error" in r:
            continue
        t = r["timing"]
        timing_patterns.append({
            "dataset": r["dataset"],
            "t5_faster": t["t5_faster"],
            "t5_median": t["t5_median"],
            "t3_median": t["t3_median"],
            "fast_lift": t["fast_lift"],
        })

    # Supplier patterns
    supplier_patterns = []
    for r in results:
        if "error" in r:
            continue
        s = r["supplier"]
        supplier_patterns.append({
            "dataset": r["dataset"],
            "t5_missing": s["t5_missing_rate"],
            "t3_missing": s["t3_missing_rate"],
            "lift": s["lift"],
        })

    # Write aggregated report
    report = {
        "datasets_processed": len(results),
        "datasets": [r["dataset"] for r in results if "error" not in r],
        "signal_generalization": {
            sig: {
                "appears_in": len(lifts),
                "avg_lift": round(sum(l for _, l, _, _ in lifts) / len(lifts), 2),
                "datasets_with_lift_gt_2": sum(1 for _, l, _, _ in lifts if l > 2),
                "datasets_with_lift_gt_5": sum(1 for _, l, _, _ in lifts if l > 5),
                "per_dataset": [{"dataset": d, "lift": l, "t5_rate": t5r, "t3_rate": t3r} for d, l, t5r, t3r in lifts],
            }
            for sig, lifts in sorted(signal_lifts.items(), key=lambda x: -sum(1 for _, l, _, _ in x[1] if l > 2))
        },
        "timing_patterns": timing_patterns,
        "supplier_patterns": supplier_patterns,
        "per_dataset_results": results,
    }

    (OUTPUT_BASE / "cross_dataset_generalization_report.json").write_text(json.dumps(report, indent=2))

    # Print summary
    print(f"\n=== Cross-dataset signal generalization ({len(results)} datasets) ===\n")
    print(f"{'Signal':<30} {'Appears':>8} {'Avg':>6} {'Lift>2':>7} {'Lift>5':>7}")
    for sig, data in report["signal_generalization"].items():
        print(f"{sig:<30} {data['appears_in']:>8} {data['avg_lift']:>6.1f} {data['datasets_with_lift_gt_2']:>7} {data['datasets_with_lift_gt_5']:>7}")

    print(f"\n=== Timing patterns ===")
    print(f"{'Dataset':<40} {'t5_med':>7} {'t3_med':>7} {'t5_faster':>10} {'fast_lift':>10}")
    for t in timing_patterns:
        print(f"{t['dataset']:<40} {t['t5_median']:>7.0f} {t['t3_median']:>7.0f} {str(t['t5_faster']):>10} {t['fast_lift']:>10.1f}")

    print(f"\n=== Supplier patterns ===")
    print(f"{'Dataset':<40} {'t5_miss':>8} {'t3_miss':>8} {'lift':>6}")
    for s in supplier_patterns:
        print(f"{s['dataset']:<40} {s['t5_missing']:>8.1%} {s['t3_missing']:>8.1%} {s['lift']:>6.1f}")


if __name__ == "__main__":
    main()
