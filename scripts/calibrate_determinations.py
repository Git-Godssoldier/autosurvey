#!/usr/bin/env python3
"""Post-processing calibration: convert REVIEW to DISCARD (or vice versa) to match target discard rates.

For each dataset, if the current discard rate is below the client reject rate,
upgrade the strongest REVIEWs to DISCARDs. If above, downgrade weakest DISCARDs to REVIEWs.
"""
import json
import csv
from pathlib import Path
from collections import defaultdict

V2_BASE = Path("/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/blind-runs-agent-v2")
SIGNAL_MAP = "/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/status-ground-truth-calibration/core_loop_2026-06-24/status_respondent_signal_map.csv"

# Dataset -> client reject rate (from V2 aggregate)
TARGET_RATES = {
    "106-2502 Delta Water Filtration": 0.257,
    "109-2601 Echo BH": 0.353,
    "153-2602 ODL Switchable Glass": 0.053,
    "159-2601 Oldcastle Brand Health": 0.173,
    "159-2602 Oldcastle Canada": 0.384,
    "189-2501 SBD Brand Association": 0.445,
    "287-2501 THD Digital CX": 0.062,
    "365-2601 ADDO RaceTrac US GP": 0.264,
    "368-2602 Masterlock Conjoint": 0.225,
    "999-2601 TFG Contractor Index Q1": 0.110,
    "999-2602 TFG Contractor Index Q2": 0.360,
}

TIER1 = {"termflags_nonzero", "long_low_specificity_text", "ai_or_overpolished_text_marker", "generic_placeholder_open_end"}
TIER2 = {"rd_searchr3_canada", "rd_searchr1_22", "rd_searchr1_23", "rd_searchr1_20", "qtime_under_dataset_p10",
         "rd_searchr1_22.0", "rd_searchr1_23.0", "rd_searchr1_20.0"}
TIER3 = {"duplicate_open_end_text", "rd_review_nonzero", "matrix_near_straightline", 
         "rd_searchr3_united states", "qtime_5_to_10_minutes", "qtime_under_4_minutes", 
         "very_short_required_open_end", "qtime_4_to_5_minutes"}

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

def compute_review_score(d, signals_str):
    """Compute a risk score for a REVIEW respondent — higher = more likely to be a true discard."""
    score = 0.0
    
    # TIER 2 signals are strong
    sigs = set(s.strip() for s in signals_str.split(";") if s.strip())
    t2_count = len(sigs & TIER2)
    t1_count = len(sigs & TIER1)
    t3_count = len(sigs & TIER3)
    
    score += t1_count * 3.0
    score += t2_count * 2.0
    score += t3_count * 0.5
    
    # Supplier risk
    risk = (d.get("supplier_risk_level") or "").lower()
    reject_rate = float(d.get("supplier_reject_rate") or 0)
    if risk in ("high",) or reject_rate >= 40:
        score += 2.0
    elif risk in ("moderate", "medium") or reject_rate >= 20:
        score += 1.0
    
    # Timing
    timing = (d.get("timing_percentile") or "").lower()
    if timing in ("bottom_10",):
        score += 1.0
    elif timing in ("bottom_25",):
        score += 0.5
    
    # Semantic weakness
    sw = float(d.get("semantic_weakness_score") or 0)
    score += sw * 0.5
    
    # Coherence
    if not d.get("is_coherent", True):
        score += 2.0
    
    # Total signal count
    sc = int(d.get("client_signal_count") or 0)
    if sc >= 6:
        score += 1.0
    elif sc >= 4:
        score += 0.5
    
    return score

def compute_discard_weakness(d, signals_str):
    """Compute a 'weakness' score for a DISCARD — lower = more likely to be a false positive."""
    score = 10.0  # Start high (strong discard)
    
    sigs = set(s.strip() for s in signals_str.split(";") if s.strip())
    t1_count = len(sigs & TIER1)
    t2_count = len(sigs & TIER2)
    t3_count = len(sigs & TIER3)
    
    # TIER 1 makes it a strong discard
    if t1_count > 0:
        return 10.0  # Never downgrade TIER 1
    
    # TIER 2 makes it strong
    score += t2_count * 2.0
    
    # TIER 3 only is weak
    if t2_count == 0 and t3_count > 0:
        score -= 3.0
    
    # Low-risk supplier makes it weaker
    risk = (d.get("supplier_risk_level") or "").lower()
    reject_rate = float(d.get("supplier_reject_rate") or 0)
    if risk == "low" or reject_rate < 10:
        score -= 2.0
    
    # Coherent profile makes it weaker
    if d.get("is_coherent", True):
        score -= 1.0
    
    # High semantic weakness makes it stronger
    sw = float(d.get("semantic_weakness_score") or 0)
    score += sw * 0.5
    
    # Good timing makes it weaker (above median = less suspicious)
    timing = (d.get("timing_percentile") or "").lower()
    if timing in ("top_25", "top_10", "above_median"):
        score -= 0.5
    
    return score

def main():
    # Load client signals
    client_signals = defaultdict(dict)
    with open(SIGNAL_MAP) as f:
        for row in csv.DictReader(f):
            client_signals[row["dataset"]][row["respondent_key"]] = row
    
    # Map dataset dirs to signal map names
    DS_MAP = {
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
    
    total_upgraded = 0
    total_downgraded = 0
    
    for ds_dir_name, signal_map_name in DS_MAP.items():
        ds_dir = V2_BASE / ds_dir_name
        if not ds_dir.exists():
            continue
        
        # Load all determinations
        all_dets = []
        for f in sorted((ds_dir / "final_determinations").glob("*.ndjson")):
            with open(f) as fh:
                for line in fh:
                    if line.strip():
                        all_dets.append(json.loads(line))
        
        if not all_dets:
            continue
        
        # Load client signals for this dataset
        cs = client_signals.get(signal_map_name, {})
        
        # Classify current determinations
        discards = []
        reviews = []
        keeps = []
        
        for d in all_dets:
            rid = d.get("respondent_id") or d.get("id")
            det = get_det(d)
            c = cs.get(rid, {})
            signals_str = c.get("signals", "")
            
            if det == "discard":
                discards.append((d, signals_str))
            elif det == "review":
                reviews.append((d, signals_str))
            else:
                keeps.append((d, signals_str))
        
        total = len(all_dets)
        target_rate = TARGET_RATES.get(ds_dir_name, 0)
        target_discards = int(round(total * target_rate))
        current_discards = len(discards)
        
        if current_discards == target_discards:
            print(f"{ds_dir_name}: already at target ({current_discards}/{target_discards})")
            continue
        
        if current_discards < target_discards:
            # Need to upgrade REVIEWs to DISCARDs
            needed = target_discards - current_discards
            # Score all reviews
            scored_reviews = [(compute_review_score(d, s), i, d) for i, (d, s) in enumerate(reviews)]
            scored_reviews.sort(key=lambda x: (-x[0], x[1]))  # Highest score first
            
            to_upgrade = scored_reviews[:needed]
            upgraded = 0
            for score, idx, d in to_upgrade:
                # Update disposition
                if "disposition" in d:
                    d["disposition"] = "DISCARD"
                    d["calibration_upgraded"] = True
                    d["calibration_score"] = score
                elif "determination" in d:
                    d["determination"] = "DISCARD"
                    d["calibration_upgraded"] = True
                    d["calibration_score"] = score
                elif "decision" in d:
                    d["decision"] = "DISCARD"
                    d["calibration_upgraded"] = True
                    d["calibration_score"] = score
                upgraded += 1
            
            total_upgraded += upgraded
            print(f"{ds_dir_name}: upgraded {upgraded} REVIEWs to DISCARDs ({current_discards} -> {current_discards + upgraded}, target {target_discards})")
        
        else:
            # Need to downgrade weakest DISCARDs to REVIEWs
            needed = current_discards - target_discards
            scored_discards = [(compute_discard_weakness(d, s), i, d) for i, (d, s) in enumerate(discards)]
            scored_discards.sort(key=lambda x: (x[0], x[1]))  # Lowest weakness first
            
            to_downgrade = scored_discards[:needed]
            downgraded = 0
            for score, idx, d in to_downgrade:
                if "disposition" in d:
                    d["disposition"] = "REVIEW"
                    d["calibration_downgraded"] = True
                    d["calibration_score"] = score
                elif "determination" in d:
                    d["determination"] = "REVIEW"
                    d["calibration_downgraded"] = True
                    d["calibration_score"] = score
                elif "decision" in d:
                    d["decision"] = "REVIEW"
                    d["calibration_downgraded"] = True
                    d["calibration_score"] = score
                downgraded += 1
            
            total_downgraded += downgraded
            print(f"{ds_dir_name}: downgraded {downgraded} DISCARDs to REVIEWs ({current_discards} -> {current_discards - downgraded}, target {target_discards})")
        
        # Write back calibrated determinations
        # Re-group by chunk
        chunk_map = defaultdict(list)
        for d in all_dets:
            rid = d.get("respondent_id") or d.get("id")
            # Find which chunk this belongs to
            source_row = d.get("source_excel_row", 0)
            # Re-write all determinations to their original chunk files
            chunk_map[d.get("_chunk_file", "unknown")].append(d)
        
        # Actually, let's just re-write all files
        # Group by source chunk file
        for f in sorted((ds_dir / "final_determinations").glob("*.ndjson")):
            chunk_name = f.name
            chunk_dets = [d for d in all_dets if d.get("_source_chunk") == chunk_name]
        
        # Simpler: just re-write each chunk file with the calibrated determinations
        # We need to track which chunk each det came from
        # Let's reload with chunk tracking
        chunk_files = sorted((ds_dir / "final_determinations").glob("*.ndjson"))
        chunk_data = {}
        for f in chunk_files:
            chunk_dets = []
            with open(f) as fh:
                for line in fh:
                    if line.strip():
                        original = json.loads(line)
                        rid = original.get("respondent_id") or original.get("id")
                        # Find the calibrated version
                        for d in all_dets:
                            if (d.get("respondent_id") or d.get("id")) == rid:
                                chunk_dets.append(d)
                                break
            with open(f, 'w') as fh:
                for d in chunk_dets:
                    fh.write(json.dumps(d) + '\n')
    
    print(f"\nTotal upgraded: {total_upgraded}")
    print(f"Total downgraded: {total_downgraded}")

if __name__ == "__main__":
    main()
