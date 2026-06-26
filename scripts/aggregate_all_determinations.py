#!/usr/bin/env python3
"""Aggregate all final determinations across all 11 blind-run datasets."""

import json
import os
from pathlib import Path
from collections import Counter

BASE = Path("/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/blind-runs-agent")

def get_determination(record):
    """Extract determination from record, handling schema variations."""
    det = (record.get("determination") or record.get("decision") or
           record.get("verdict") or record.get("status") or
           record.get("classification") or "")
    return det.lower().strip()

def load_determinations(dataset_dir):
    """Load all determination files from a dataset directory."""
    det_dir = dataset_dir / "final_determinations"
    if not det_dir.exists():
        return []
    records = []
    for f in sorted(det_dir.glob("*.ndjson")):
        with open(f) as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return records

def main():
    datasets = sorted([d for d in BASE.iterdir() if d.is_dir()])
    
    all_results = {}
    total_counts = Counter()
    total_respondents = 0
    
    for ds in datasets:
        name = ds.name
        records = load_determinations(ds)
        if not records:
            print(f"WARNING: No determinations found for {name}")
            continue
        
        counts = Counter()
        for r in records:
            det = get_determination(r)
            # Normalize: "reject" -> "discard", "authentic" -> "keep", "not authentic" -> "discard"
            if det in ("reject", "not authentic", "discard", "not_authentic"):
                det = "discard"
            elif det in ("review", "concerning"):
                det = "review"
            elif det in ("keep", "authentic"):
                det = "keep"
            counts[det] += 1
            total_counts[det] += 1
            total_respondents += 1
        
        all_results[name] = {
            "total": len(records),
            "discard": counts.get("discard", 0),
            "review": counts.get("review", 0),
            "keep": counts.get("keep", 0),
            "discard_pct": round(counts.get("discard", 0) / len(records) * 100, 1),
            "review_pct": round(counts.get("review", 0) / len(records) * 100, 1),
            "keep_pct": round(counts.get("keep", 0) / len(records) * 100, 1),
        }
    
    # Print summary table
    print(f"\n{'='*120}")
    print(f"AGGREGATE QUALITY SCORING RESULTS — ALL 11 BLIND-RUN DATASETS")
    print(f"{'='*120}")
    print(f"\n{'Dataset':<45} {'Total':>7} {'Discard':>8} {'Review':>8} {'Keep':>8} {'Disc%':>7} {'Rev%':>7} {'Keep%':>7}")
    print(f"{'-'*45} {'-'*7} {'-'*8} {'-'*8} {'-'*8} {'-'*7} {'-'*7} {'-'*7}")
    
    for name, r in sorted(all_results.items()):
        print(f"{name:<45} {r['total']:>7} {r['discard']:>8} {r['review']:>8} {r['keep']:>8} {r['discard_pct']:>6.1f}% {r['review_pct']:>6.1f}% {r['keep_pct']:>6.1f}%")
    
    print(f"{'-'*45} {'-'*7} {'-'*8} {'-'*8} {'-'*8} {'-'*7} {'-'*7} {'-'*7}")
    print(f"{'TOTAL':<45} {total_respondents:>7} {total_counts['discard']:>8} {total_counts['review']:>8} {total_counts['keep']:>8} {total_counts['discard']/total_respondents*100:>6.1f}% {total_counts['review']/total_respondents*100:>6.1f}% {total_counts['keep']/total_respondents*100:>6.1f}%")
    
    # Write JSON summary
    summary = {
        "total_respondents": total_respondents,
        "total_discard": total_counts["discard"],
        "total_review": total_counts["review"],
        "total_keep": total_counts["keep"],
        "overall_discard_pct": round(total_counts["discard"] / total_respondents * 100, 1),
        "overall_review_pct": round(total_counts["review"] / total_respondents * 100, 1),
        "overall_keep_pct": round(total_counts["keep"] / total_respondents * 100, 1),
        "datasets": all_results,
    }
    
    out_path = BASE / "aggregate_summary.json"
    with open(out_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"\nSummary written to: {out_path}")

if __name__ == "__main__":
    main()
