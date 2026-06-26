#!/usr/bin/env python3
"""
Agent v2 feature loader with coverage gating.

Key principles:
1. Never encode missing agent evidence as negative evidence
2. Add explicit coverage fields (agent_record_found, agent_decision_available, etc.)
3. Use categorical rule encoding (one-hot), not ordinal rule numbers
4. Preserve missingness indicators rather than fillna(0)
5. Gate agent features by dataset coverage rate
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from collections import Counter
import numpy as np
import pandas as pd

AGENT_V2_DIR = Path("/Users/jeremyalston/Perfect/TFG Data Cleaning Sets/autosurvey-outputs/blind-runs-agent-v2")

# Map annotated dataset filenames to agent v2 directory names
DATASET_TO_AGENT = {
    "260111_Delta Water Filtration.xlsx": "106-2502 Delta Water Filtration",
    "260300_ECHO.xlsx": "109-2601 Echo BH",
    "260501_ODL.xlsx": "153-2602 ODL Switchable Glass",
    "260206_OC BH.xlsx": "159-2601 Oldcastle Brand Health",
    "260401_ OC CAN.xlsx": "159-2602 Oldcastle Canada",
    "260200_SBD.xlsx": "189-2501 SBD Brand Association",
    "251101_THD CX.xlsx": "287-2501 THD Digital CX",
    "260404_ADDO.xlsx": "365-2601 ADDO RaceTrac US GP",
    "260403_Masterlock Conjoint.xlsx": "368-2602 Masterlock Conjoint",
    "251205_TFG Contractor Index Q1.xlsx": "999-2601 TFG Contractor Index Q1",
    "260306_TFG Contractor Index Q2.xlsx": "999-2602 TFG Contractor Index Q2",
}

# Known rule families for categorical encoding
RULE_FAMILIES = ["keep", "discard", "review", "calibration", "fallback", "unknown"]

_agent_cache = {}
_packet_cache = {}
_coverage_cache = {}


def load_agent_determinations(dataset_name):
    """Load agent v2 determinations for a dataset."""
    if dataset_name in _agent_cache:
        return _agent_cache[dataset_name]
    
    agent_dir = DATASET_TO_AGENT.get(dataset_name)
    if not agent_dir:
        _agent_cache[dataset_name] = {}
        return {}
    
    det_dir = AGENT_V2_DIR / agent_dir / "final_determinations"
    if not det_dir.exists():
        _agent_cache[dataset_name] = {}
        return {}
    
    dets = {}
    for f in sorted(det_dir.glob("*.ndjson")):
        for line in open(f):
            d = json.loads(line)
            dets[d["respondent_id"]] = d
    
    _agent_cache[dataset_name] = dets
    return dets


def load_staged_packets(dataset_name):
    """Load staged packets with answer chains for a dataset."""
    if dataset_name in _packet_cache:
        return _packet_cache[dataset_name]
    
    agent_dir = DATASET_TO_AGENT.get(dataset_name)
    if not agent_dir:
        _packet_cache[dataset_name] = {}
        return {}
    
    packet_file = AGENT_V2_DIR / agent_dir / "staged_packets.ndjson"
    if not packet_file.exists():
        _packet_cache[dataset_name] = {}
        return {}
    
    packets = {}
    for line in open(packet_file):
        d = json.loads(line)
        packets[d["respondent_id"]] = d
    
    _packet_cache[dataset_name] = packets
    return packets


def get_agent_coverage(dataset_name):
    """Check what fraction of respondents have meaningful agent v2 determinations.
    
    Returns dict with:
    - record_found_rate: fraction with any det record
    - decision_available_rate: fraction with non-KEEP/non-? decisions
    - tier_signals_rate: fraction with any tier1/tier2 signals
    - has_meaningful_data: True if decision_available_rate > 0.05
    """
    if dataset_name in _coverage_cache:
        return _coverage_cache[dataset_name]
    
    dets = load_agent_determinations(dataset_name)
    if not dets:
        result = {
            "record_found_rate": 0.0,
            "decision_available_rate": 0.0,
            "tier_signals_rate": 0.0,
            "has_meaningful_data": False,
        }
        _coverage_cache[dataset_name] = result
        return result
    
    total = len(dets)
    if total == 0:
        result = {
            "record_found_rate": 0.0,
            "decision_available_rate": 0.0,
            "tier_signals_rate": 0.0,
            "has_meaningful_data": False,
        }
        _coverage_cache[dataset_name] = result
        return result
    
    meaningful = sum(1 for d in dets.values() if d.get("decision") in ("DISCARD", "REVIEW"))
    has_tiers = sum(1 for d in dets.values() if d.get("tier1_signals") or d.get("tier2_signals"))
    
    result = {
        "record_found_rate": 1.0,  # All records in dets were found
        "decision_available_rate": meaningful / total,
        "tier_signals_rate": has_tiers / total,
        "has_meaningful_data": (meaningful / total) > 0.05,
    }
    _coverage_cache[dataset_name] = result
    return result


def _classify_rule(rule_value):
    """Classify a rule into a family for categorical encoding.
    
    Returns one of: keep, discard, review, calibration, fallback, unknown
    """
    if rule_value is None or rule_value == "" or rule_value == 0:
        return "unknown"
    
    rule_str = str(rule_value).upper().strip()
    
    if rule_str == "?" or rule_str == "NONE":
        return "unknown"
    
    if "CALIBRATION" in rule_str:
        return "calibration"
    
    if "FALLBACK" in rule_str:
        return "fallback"
    
    if "DISCARD" in rule_str:
        return "discard"
    
    if "REVIEW" in rule_str:
        return "review"
    
    if "KEEP" in rule_str:
        return "keep"
    
    # Numeric rules: 4=discard, 8=keep, 9=keep
    if isinstance(rule_value, (int, float)):
        if rule_value == 4:
            return "discard"
        elif rule_value in (8, 9):
            return "keep"
        elif rule_value in (1, 2, 3):
            return "discard"
    
    return "unknown"


def extract_agent_features(df, dataset_name):
    """Extract agent v2 features for each respondent in the dataframe.
    
    Includes coverage indicators and categorical rule encoding.
    Missing agent evidence is preserved as NaN with missingness indicators,
    NOT filled with zeros.
    """
    dets = load_agent_determinations(dataset_name)
    packets = load_staged_packets(dataset_name)
    coverage = get_agent_coverage(dataset_name)
    
    features = pd.DataFrame(index=df.index)
    
    for idx, row in df.iterrows():
        rid = row["respondent_id"]
        det = dets.get(rid, {})
        pkt = packets.get(rid, {})
        
        # === COVERAGE INDICATORS (always available) ===
        record_found = 1 if det else 0
        decision_available = 1 if det and det.get("decision") in ("DISCARD", "REVIEW", "KEEP") else 0
        tier_signals_available = 1 if det and (det.get("tier1_signals") or det.get("tier2_signals")) else 0
        justification_available = 1 if det and det.get("justification") else 0
        
        features.loc[idx, "agent_record_found"] = record_found
        features.loc[idx, "agent_decision_available"] = decision_available
        features.loc[idx, "agent_tier_signals_available"] = tier_signals_available
        features.loc[idx, "agent_justification_available"] = justification_available
        
        # === AGENT DECISION FEATURES (only if record found) ===
        if record_found and decision_available:
            decision = det.get("decision", "UNKNOWN")
            features.loc[idx, "agent_decision_discard"] = 1.0 if decision == "DISCARD" else 0.0
            features.loc[idx, "agent_decision_review"] = 1.0 if decision == "REVIEW" else 0.0
            features.loc[idx, "agent_decision_keep"] = 1.0 if decision == "KEEP" else 0.0
        else:
            # Missing - use NaN, not 0
            features.loc[idx, "agent_decision_discard"] = np.nan
            features.loc[idx, "agent_decision_review"] = np.nan
            features.loc[idx, "agent_decision_keep"] = np.nan
        
        # === CATEGORICAL RULE ENCODING (one-hot, not ordinal) ===
        if record_found:
            rule = det.get("rule_applied", "?")
            rule_family = _classify_rule(rule)
        else:
            rule_family = "unknown"
        
        for family in RULE_FAMILIES:
            features.loc[idx, f"agent_rule_{family}"] = 1.0 if rule_family == family else 0.0
        
        # === AGENT TIER SIGNAL COUNTS (only if available) ===
        if tier_signals_available:
            t1 = det.get("tier1_signals", [])
            t2 = det.get("tier2_signals", [])
            t3 = det.get("tier3_signals", [])
            features.loc[idx, "agent_t1_count"] = float(len(t1))
            features.loc[idx, "agent_t2_count"] = float(len(t2))
            features.loc[idx, "agent_t3_count"] = float(len(t3))
            features.loc[idx, "agent_has_t1"] = 1.0 if len(t1) > 0 else 0.0
            features.loc[idx, "agent_has_t2"] = 1.0 if len(t2) > 0 else 0.0
        else:
            features.loc[idx, "agent_t1_count"] = np.nan
            features.loc[idx, "agent_t2_count"] = np.nan
            features.loc[idx, "agent_t3_count"] = np.nan
            features.loc[idx, "agent_has_t1"] = np.nan
            features.loc[idx, "agent_has_t2"] = np.nan
        
        # === AGENT SUPPLIER FEATURES (only if available) ===
        if record_found and "supplier_reject_rate" in det:
            features.loc[idx, "agent_supplier_risk_rate"] = float(det.get("supplier_reject_rate", 0))
            features.loc[idx, "agent_supplier_high_risk"] = 1.0 if det.get("supplier_risk_level") == "high" else 0.0
            features.loc[idx, "agent_supplier_medium_risk"] = 1.0 if det.get("supplier_risk_level") in ("medium", "moderate") else 0.0
        else:
            features.loc[idx, "agent_supplier_risk_rate"] = np.nan
            features.loc[idx, "agent_supplier_high_risk"] = np.nan
            features.loc[idx, "agent_supplier_medium_risk"] = np.nan
        
        # === AGENT TIMING FEATURES (from det if available, else from packet) ===
        if record_found and det.get("timing_percentile"):
            tp = det.get("timing_percentile", "")
            features.loc[idx, "agent_timing_bottom_10"] = 1.0 if "bottom_10" in tp else 0.0
            features.loc[idx, "agent_timing_below_median"] = 1.0 if "below_median" in tp or "bottom" in tp else 0.0
            features.loc[idx, "agent_qtime_minutes"] = float(det.get("qtime_minutes", 0))
        elif pkt and pkt.get("timing_percentile"):
            tp = pkt.get("timing_percentile", "")
            features.loc[idx, "agent_timing_bottom_10"] = 1.0 if "bottom_10" in tp else 0.0
            features.loc[idx, "agent_timing_below_median"] = 1.0 if "below_median" in tp or "bottom" in tp else 0.0
            features.loc[idx, "agent_qtime_minutes"] = float(pkt.get("qtime_minutes", 0))
        else:
            features.loc[idx, "agent_timing_bottom_10"] = np.nan
            features.loc[idx, "agent_timing_below_median"] = np.nan
            features.loc[idx, "agent_qtime_minutes"] = np.nan
    
    # Dataset-level coverage rate as a feature
    features["agent_coverage_rate"] = coverage["decision_available_rate"]
    features["agent_has_meaningful_data"] = 1.0 if coverage["has_meaningful_data"] else 0.0
    
    return features


def get_agent_justification_text(df, dataset_name):
    """Get the agent justification text for each respondent (for TF-IDF)."""
    dets = load_agent_determinations(dataset_name)
    texts = []
    for _, row in df.iterrows():
        rid = row["respondent_id"]
        det = dets.get(rid, {})
        texts.append(det.get("justification", ""))
    return texts


def get_answer_chain_text(df, dataset_name):
    """Get the answer chain as text for each respondent (semantic reconstruction TF-IDF)."""
    packets = load_staged_packets(dataset_name)
    texts = []
    for _, row in df.iterrows():
        rid = row["respondent_id"]
        pkt = packets.get(rid, {})
        chain = pkt.get("answer_chain", [])
        parts = []
        for a in chain:
            label = a.get("label", "") or a.get("raw_value", "")
            if label:
                parts.append(str(label))
        texts.append(" ".join(parts))
    return texts


def get_question_answer_pairs(df, dataset_name):
    """Get question-answer pairs as text for semantic coherence analysis."""
    packets = load_staged_packets(dataset_name)
    texts = []
    for _, row in df.iterrows():
        rid = row["respondent_id"]
        pkt = packets.get(rid, {})
        chain = pkt.get("answer_chain", [])
        parts = []
        for a in chain:
            q = a.get("question_text", "")
            ans = a.get("label", "") or a.get("raw_value", "")
            if q and ans:
                parts.append(f"{q} [ANS] {ans}")
        texts.append(" [SEP] ".join(parts))
    return texts
