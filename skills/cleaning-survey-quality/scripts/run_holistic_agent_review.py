#!/usr/bin/env python3
"""Holistic Agent Review Pipeline — Phase 1: Generate comprehensive review packets.

This script builds review packets that include the FULL answer chain with all
signals: per-grid straightlining analysis, all open-end fields with question
text, survey defender flags (qc, TERMFLAGS, RD_Search), timing, supplier risk,
LangAssess readability, duplicate counts, and ML triage score.

Key insight from miss analysis:
- The `outro` field is a QC question asking "describe what this survey was about"
  → Generic topic restatements are EXPECTED, not fraud signals
- q14 ("What prompted you to decide to buy?") is the key open-end for personal experience
- Missing q14 is NOT a discard signal for this client
- ML triage > 0.7 correlates with true discards
- Per-grid straightlining matters (some grids are naturally uniform)

Usage:
    python3 run_holistic_agent_review.py <xlsx_path> [--output-dir DIR] [--review-all] [--chunk-size N]
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import openpyxl

# Add the skills scripts directory
SKILL_SCRIPTS = Path(__file__).parent
sys.path.insert(0, str(SKILL_SCRIPTS))

from survey_pipeline import (
    extract_features_and_chain,
    ml_triage,
    clean,
    norm,
    parse_datamap,
    classify_field,
)


def identify_grid_groups(headers, roles):
    """Group matrix columns by question prefix (e.g., q3r1-q3r12 = grid q3)."""
    grids = defaultdict(list)
    for i, h in enumerate(headers):
        if h and roles.get(str(h)) == "matrix_cell":
            # Extract grid prefix: q3r1 -> q3, q5r1c1 -> q5
            m = re.match(r"(q\d+)[a-z]?\d+", str(h).lower())
            if m:
                grids[m.group(1)].append((i, str(h)))
    return dict(grids)


def analyze_per_grid_straightlining(row, grids, hidx):
    """Analyze straightlining for each grid separately.
    
    Returns dict: {grid_name: {unique_ratio, straightline, n_items, values}}
    """
    results = {}
    for grid_name, cols in grids.items():
        vals = []
        for i, h in cols:
            if i < len(row) and row[i] is not None and row[i] != "":
                vals.append(norm(row[i]))
        if not vals:
            continue
        unique = len(set(vals))
        ur = unique / len(vals)
        results[grid_name] = {
            "n_items": len(vals),
            "n_unique": unique,
            "unique_ratio": round(ur, 3),
            "straightline": 1 if ur <= 0.2 and len(vals) >= 3 else 0,
            "values": [str(v) for v in vals],
        }
    return results


def get_all_oe_fields(row, oe_cols, datamap):
    """Get all open-end fields with their question text and response."""
    results = []
    for i, h in oe_cols:
        if i >= len(row):
            continue
        val = clean(row[i])
        if not val:
            continue
        dm = datamap.get(str(h), {})
        qtext = dm.get("question_text", str(h))
        results.append({
            "field": str(h),
            "question": qtext[:200],
            "response": val[:500],
            "char_count": len(val),
        })
    return results


def get_defender_signals(row, hidx):
    """Extract survey defender / quality control signals."""
    signals = {}
    
    # qc — quality control flag (1-12)
    qc_idx = hidx.get("qc")
    if qc_idx and qc_idx < len(row):
        qc_val = norm(row[qc_idx])
        if qc_val and qc_val != 0:
            qc_labels = {
                1: "Not select 3", 2: "State mismatch", 3: "Red Herring",
                4: "REGION mismatch", 5: "AGE mismatch", 6: "RD /REVIEW rejection",
                7: "OE screening", 8: "RD /SEARCH threat rejection",
                9: "RD /SEARCH duplicate rejection", 10: "RD /SEARCH country rejection",
                11: "Speeder", 12: "Exceeded number of terms",
            }
            signals["qc_flag"] = qc_val
            signals["qc_label"] = qc_labels.get(qc_val, f"Unknown QC flag {qc_val}")
    
    # TERMFLAGS
    tf_idx = hidx.get("TERMFLAGS")
    if tf_idx and tf_idx < len(row):
        tf = norm(row[tf_idx])
        if tf and tf != 0:
            signals["termflags"] = tf
    
    # RD_Search signals (survey defender)
    for field in ["RD_Searchr0", "RD_Searchr1", "RD_Searchr2", "RD_Searchr3",
                   "RD_Searchr4", "RD_Searchr5", "RD_Searchr6", "RD_Searchr7"]:
        idx = hidx.get(field)
        if idx and idx < len(row):
            val = row[idx]
            if val is not None and val != "" and val != 0:
                signals[field] = norm(val)
    
    # RD_GetToken
    for field in ["RD_GetTokenr0", "RD_GetTokenr1"]:
        idx = hidx.get(field)
        if idx and idx < len(row):
            val = row[idx]
            if val is not None and val != "":
                signals[field] = str(val)[:50]
    
    # outroR1_RD_Review (review flags on outro)
    for field in ["outroR1_RD_Reviewr0", "outroR1_RD_Reviewr1", "outroR1_RD_Reviewr2",
                   "outroR1_RD_Reviewr3", "outroR1_RD_Reviewr4"]:
        idx = hidx.get(field)
        if idx and idx < len(row):
            val = norm(row[idx])
            if val is not None and val != "" and val != 0:
                signals[field] = val
    
    return signals


def get_key_answers(row, hidx, datamap):
    """Extract key single-choice and demographic answers for context."""
    key_fields = {
        "q1": "Industry",
        "q2": "Home ownership",
        "q6": "Shopping stage",
        "q8a": "Kitchen filtration type (have)",
        "q8b": "Kitchen filtration type (plan)",
        "q9": "Bathroom filtration type",
        "q12": "Bath role (children)",
        "q13": "Purchase role",
        "q15": "Water quality concern level",
        "q16": "Knowledge of water filter",
        "q28": "Purchase location",
        "q30": "Water source",
        "qHomeType": "Home type",
        "qGender": "Gender",
        "qUSHHI": "Household income",
        "age": "Age",
        "REGION": "Region",
    }
    answers = {}
    for field, label in key_fields.items():
        idx = hidx.get(field)
        if idx and idx < len(row):
            val = norm(row[idx])
            if val is not None and val != "":
                dm = datamap.get(field, {})
                value_label = dm.get("labels", {}).get(str(val), str(val))
                answers[label] = value_label
    return answers


def build_holistic_review_packets(filepath, output_dir, review_all=False, chunk_size=200):
    """Build comprehensive review packets for all respondents."""
    filepath = Path(filepath)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*80}")
    print(f"HOLISTIC AGENT REVIEW — Building Review Packets")
    print(f"{'='*80}")
    print(f"  Input: {filepath.name}")
    print(f"  Output: {output_dir}")

    # Load workbook
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    ws = wb["A1"] if "A1" in wb.sheetnames else wb[wb.sheetnames[0]]
    headers = [c.value for c in next(ws.iter_rows(min_row=1, max_row=1))]
    hidx = {h: i for i, h in enumerate(headers) if h}

    datamap = parse_datamap(wb)
    roles = {str(h): classify_field(str(h)) for h in headers if h}

    # Identify column groups
    oe_cols = [(i, h) for i, h in enumerate(headers) if h and roles.get(str(h)) == "open_end"]

    # Also identify open-end fields from datamap (fields with no value labels = text fields)
    # This catches fields like q14 that don't end in "oe"
    oe_field_names = {h for _, h in oe_cols}
    technical_qtext = {"captured variable", "open text response", "open numeric response",
                       "open-ended response", ""}
    for i, h in enumerate(headers):
        if h and str(h) not in oe_field_names:
            dm = datamap.get(str(h), {})
            qtext = dm.get("question_text", "").lower().strip()
            # If the field has question text but no labels, it's likely an open-end text field
            # Exclude technical "Captured variable" and generic "Open text response" fields
            if dm.get("question_text") and not dm.get("labels") and qtext not in technical_qtext:
                # Verify it's not a known non-OE field
                if roles.get(str(h)) not in ("id", "label", "timing", "supplier", "ip",
                    "user_agent", "timestamp", "technical", "nlp_metadata", "review_metadata",
                    "quality_flag", "paste_flag", "no_answer", "routing", "quota"):
                    oe_cols.append((i, h))
                    oe_field_names.add(str(h))

    lang_cols = [(i, h) for i, h in enumerate(headers) if h and roles.get(str(h)) == "nlp_metadata"]
    grids = identify_grid_groups(headers, roles)

    print(f"  Open-end fields: {len(oe_cols)}")
    print(f"  Grid groups: {len(grids)} ({list(grids.keys())[:10]}...)")
    print(f"  Datamap fields: {len(datamap)}")

    # Run the standard pipeline for ML triage + features
    print(f"\n  Running ML triage + feature extraction...")
    df, _, _, answer_chains = extract_features_and_chain(filepath)
    df = ml_triage(df)

    # Compute population stats
    matrix_prevalence = (df["matrix_straightline"] == 1).mean() if "matrix_straightline" in df.columns else 0
    qtime_median = float(df["qtime_minutes"].median()) if "qtime_minutes" in df.columns else 0
    qtime_p10 = float(np.percentile(df[df["qtime_minutes"] > 0]["qtime_minutes"], 10)) if "qtime_minutes" in df.columns else 0
    qtime_p25 = float(np.percentile(df[df["qtime_minutes"] > 0]["qtime_minutes"], 25)) if "qtime_minutes" in df.columns else 0

    # Supplier reject rates
    sup_rates = df.groupby("supplier_name")["signal_count"].mean().to_dict() if "signal_count" in df.columns else {}
    global_rate = float(df["signal_count"].mean()) if "signal_count" in df.columns else 0

    # OE duplicate counts (across all respondents)
    all_oe_combined = []
    for idx, row in df.iterrows():
        chain = answer_chains[idx] if idx < len(answer_chains) else {}
        all_oe_combined.append(chain.get("oe_text", ""))
    oe_ctr = Counter(t.strip().lower() for t in all_oe_combined if t.strip())

    # Per-field OE duplicate counts
    oe_field_texts = defaultdict(list)
    rows_raw = list(ws.iter_rows(min_row=2, values_only=True))
    for row in rows_raw:
        for i, h in oe_cols:
            if i < len(row):
                val = clean(row[i])
                if val:
                    oe_field_texts[str(h)].append(val.strip().lower())
    oe_field_ctr = {h: Counter(texts) for h, texts in oe_field_texts.items()}

    # Build review packets
    print(f"\n  Building review packets for {len(df)} respondents...")

    review_packets = []
    for idx, df_row in df.iterrows():
        rid = df_row["respondent_id"]
        raw_row = rows_raw[idx] if idx < len(rows_raw) else None
        if raw_row is None:
            continue

        chain = answer_chains[idx] if idx < len(answer_chains) else {}

        # Per-grid straightlining analysis
        grid_analysis = analyze_per_grid_straightlining(raw_row, grids, hidx)
        n_grids_sl = sum(1 for g in grid_analysis.values() if g["straightline"])
        n_grids_total = len(grid_analysis)
        grids_sl_list = [g for g, v in grid_analysis.items() if v["straightline"]]

        # All OE fields with question text
        oe_fields = get_all_oe_fields(raw_row, oe_cols, datamap)

        # Defender signals
        defender = get_defender_signals(raw_row, hidx)

        # Key demographic/choice answers
        key_answers = get_key_answers(raw_row, hidx, datamap)

        # LangAssess
        lang = {}
        for i, h in lang_cols:
            if i < len(raw_row) and raw_row[i] is not None:
                lang[str(h)] = float(raw_row[i]) if raw_row[i] else 0

        # Timing
        qtime_min = float(df_row.get("qtime_minutes", 0))
        qtime_pct = df_row.get("qtime_percentile", "")

        # Supplier
        supplier = str(df_row.get("supplier_name", ""))
        sup_rate = float(df_row.get("supplier_reject_rate", 0))

        # ML triage
        ml_score = float(df_row.get("ml_triage_score", 0.5))

        # OE duplicate counts per field
        oe_dups = {}
        for oe in oe_fields:
            field = oe["field"]
            text = oe["response"].strip().lower()
            if text:
                ctr = oe_field_ctr.get(field, Counter())
                oe_dups[field] = ctr.get(text, 0)

        # Build the comprehensive packet
        packet = {
            "respondent_id": rid,
            "ml_triage_score": round(ml_score, 3),
            "timing": {
                "minutes": round(qtime_min, 1),
                "percentile": qtime_pct,
                "median_minutes": round(qtime_median, 1),
            },
            "supplier": {
                "name": supplier,
                "reject_rate": round(sup_rate, 1),
            },
            "defender_signals": defender,
            "lang_assess": lang,
            "matrix_analysis": {
                "total_grids": n_grids_total,
                "grids_straightlined": n_grids_sl,
                "straightlined_grids": grids_sl_list,
                "per_grid": {g: {"unique_ratio": v["unique_ratio"], "n_items": v["n_items"], "n_unique": v["n_unique"]}
                            for g, v in grid_analysis.items()},
            },
            "open_end_responses": oe_fields,
            "oe_duplicate_counts": oe_dups,
            "key_answers": key_answers,
            "signal_count": int(df_row.get("signal_count", 0)),
            "t1_count": int(df_row.get("t1_count", 0)),
            "t2_count": int(df_row.get("t2_count", 0)),
            "answer_entropy": round(float(df_row.get("answer_entropy", 0)), 2),
            "matrix_unique_ratio": round(float(df_row.get("matrix_unique_ratio", 0)), 3),
            "oe_total_chars": int(df_row.get("oe_total_chars", 0)),
        }
        review_packets.append(packet)

    print(f"  Total packets: {len(review_packets)}")

    # Write packets in chunks
    n_chunks = (len(review_packets) + chunk_size - 1) // chunk_size
    print(f"  Chunking into {n_chunks} files of ~{chunk_size} each...")

    for chunk_idx in range(n_chunks):
        start = chunk_idx * chunk_size
        end = min(start + chunk_size, len(review_packets))
        chunk = review_packets[start:end]
        chunk_path = output_dir / f"review_chunk_{chunk_idx:02d}.json"
        with open(chunk_path, "w") as f:
            json.dump(chunk, f, indent=2)
        print(f"    Chunk {chunk_idx:02d}: {len(chunk)} packets → {chunk_path.name}")

    # Write agent instructions
    instructions = build_agent_instructions(len(review_packets), n_chunks, matrix_prevalence, filepath.name)
    instructions_path = output_dir / "agent_review_instructions.md"
    with open(instructions_path, "w") as f:
        f.write(instructions)
    print(f"  Instructions: {instructions_path.name}")

    # Write summary
    summary = {
        "dataset": filepath.name,
        "total_respondents": len(review_packets),
        "n_chunks": n_chunks,
        "chunk_size": chunk_size,
        "matrix_prevalence": round(matrix_prevalence, 3),
        "median_qtime_minutes": round(qtime_median, 1),
        "oe_fields": [h for _, h in oe_cols],
        "grid_groups": list(grids.keys()),
    }
    summary_path = output_dir / "review_summary.json"
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\n{'='*80}")
    print(f"COMPLETE — {len(review_packets)} review packets in {n_chunks} chunks")
    print(f"{'='*80}")
    print(f"\nNext: Spawn {n_chunks} subagents to review the chunks.")
    print(f"Each subagent reads review_chunk_XX.json and writes agent_judgments_chunk_XX.json")

    return review_packets


def build_agent_instructions(n_respondents, n_chunks, matrix_prevalence, dataset_name):
    """Build detailed instructions for the reviewing agent."""

    return f"""# Holistic Agent Review Instructions

## Task
Read the file `review_chunk_XX.json` (assigned to you). It contains ~200 respondent review packets.

For each respondent, you must read ALL signals holistically and assign:
- `agent_score`: -1.0 to +1.0
  - -1.0 = clear discard (fraud, bot, incoherent)
  - -0.5 = lean discard (multiple converging concerns)
  - 0.0 = uncertain / needs human review
  - +0.5 = lean keep (minor concerns but coherent)
  - +1.0 = clear keep (genuine, engaged respondent)
- `agent_judgment`: "DISCARD", "REVIEW", or "KEEP"
  - DISCARD: agent_score < -0.3
  - REVIEW: agent_score -0.3 to 0
  - KEEP: agent_score > 0
- `agent_justification`: 2-4 sentence explanation citing specific evidence from the answer chain

## Output Format
Write to `agent_judgments_chunk_XX.json` as a JSON array:
```json
[
  {{
    "respondent_id": "abc123",
    "agent_score": -0.7,
    "agent_judgment": "DISCARD",
    "agent_justification": "The q14 response ('i need it') is a non-answer. The outro is off-topic ('good night my friend'). Matrix straightlining across 8 of 10 grids. RD_Search threat score is elevated. No first-person content anywhere."
  }}
]
```

## What to Evaluate (ALL signals, holistically)

### 1. Open-End Response Quality (MOST IMPORTANT)
For EACH open-end field, read the question text and the response:

- **q14** ("What prompted you to decide to buy a water filtration device?"):
  - First-person personal experience = STRONG KEEP signal (e.g., "my water tasted like chlorine", "my kids have eczema")
  - Generic but on-topic = neutral (e.g., "cleaner water", "health concerns") — NOT a discard signal
  - Missing/empty = neutral (NOT a discard signal — client tolerates missing q14)
  - Off-topic/gibberish = discard signal (e.g., "ispring", "macus", "good night")
  - Third-person = discard signal (e.g., "people want clean water")

- **outro** ("For quality control purposes, please describe what this survey was about"):
  - This is a QC QUESTION asking what the survey was about — generic topic restatements are EXPECTED
  - "water filtration systems", "water filter survey", "about water filtration" = NORMAL, not a fraud signal
  - "this survey was about water filters" = NORMAL (the question asks this)
  - Off-topic = discard signal (e.g., "good night", "american whiskey", "customer rewards")
  - Gibberish = discard signal
  - Generic praise = mild concern (e.g., "good survey", "nice experience") but NOT a discard alone

- **Other OE fields** (q7r11oe, q8ar4oe, q8br4oe, q9r4oe, q26r15oe, q28r12oe, q30r6oe):
  - "Other (please specify)" fields — if empty, that's normal (not everyone selects "other")
  - If filled with gibberish or off-topic content = discard signal
  - If filled with relevant specific content = keep signal

### 2. Matrix/Grid Straightlining
The packet includes per-grid analysis. There are multiple grids (q3, q4, q5, q7, q10, q11, q18-q29).
- Matrix straightlining prevalence in this dataset: {matrix_prevalence:.1%}
- If ALL grids are straightlined = concern (but if prevalence is >80%, this is normal for this survey)
- If SOME grids are straightlined but others show variation = less concerning
- Look at the `straightlined_grids` list — which specific grids are uniform?
- A respondent who straightlines rating scales but varies on behavioral questions is more suspicious

### 3. Timing
- `timing.minutes` and `timing.percentile` tell you how fast they completed
- bottom_10% = very fast (concern, but not sufficient alone for discard)
- bottom_25% = fast (mild concern)
- above_median = good (protective factor)
- Very fast + generic OE + straightlining = converging concerns

### 4. Survey Defender Signals
- `defender_signals.qc_flag`: If non-zero, the platform already flagged this respondent
  - qc=6 (RD /REVIEW rejection), qc=8 (SEARCH threat), qc=9 (SEARCH duplicate) = STRONG discard
  - qc=11 (Speeder) = moderate concern
  - qc=2,4,5 (state/region/age mismatch) = strong concern
- `defender_signals.RD_Searchr1`: Threat potential score — elevated values are concerning
- `defender_signals.RD_Searchr3`: Country — if not expected country, concerning
- `defender_signals.TERMFLAGS`: Non-zero = platform flagged for termination

### 5. Supplier Risk
- `supplier.reject_rate`: Historical reject rate for this supplier
- >30% = high risk (moderate concern)
- >20% = medium risk (mild concern)
- <15% = low risk (protective factor)
- Supplier risk alone is NOT sufficient for discard — it's a multiplier on other signals

### 6. LangAssess Readability
- `lang_assess.LangAssessReadLevel`: Grade level of OE text
- Very low (<3) with long text = possible incoherence
- Very high with short text = possible AI-generated
- Normal range (5-12) = expected

### 7. Duplicate Detection
- `oe_duplicate_counts`: For each OE field, how many other respondents gave the same answer
- High dup count (>10) on unusual text = fraud signal
- High dup count on generic text ("water filtration systems") = NOT fraud (topical inevitability)
- High dup count on personal text = very suspicious (shared personal stories = fabricated)

### 8. ML Triage Score
- `ml_triage_score`: 0-1 risk probability from ML model
- >0.7 = high risk (strong signal, trust this)
- 0.4-0.7 = ambiguous
- <0.4 = low risk (protective factor)
- The ML model captures patterns we might miss — give it weight on boundary cases

### 9. Answer Entropy
- `answer_entropy`: Measures answer diversity across all questions
- Very low (<0.5) = repetitive answers across different questions = concern
- High (>2.5) = diverse answers = protective factor

## Scoring Decision Framework

### Strong DISCARD signals (score -0.7 to -1.0):
- Defender flag (qc=6,8,9) + any other concern
- Gibberish or off-topic in q14 + off-topic outro
- Off-topic outro + straightlining across most grids + very fast
- Duplicated personal story (same q14 text as many others)
- TIER 1 signal (TERMFLAGS, AI-generated text marker)

### Moderate DISCARD signals (score -0.3 to -0.5):
- Off-topic outro with no personal q14 but some answer variation
- Generic praise outro + very fast + straightlining
- Elevated RD_Search threat score + generic OE
- High-risk supplier + multiple converging concerns

### REVIEW signals (score -0.2 to 0.0):
- Mixed signals: some concerns but also some genuine content
- Fast completion but first-person q14
- Straightlining but substantive OE
- ML score 0.5-0.7 with no other strong signals

### KEEP signals (score +0.3 to +1.0):
- First-person personal q14 with specific details
- Varied matrix answers across semantically different grids
- Above-median timing
- Low-risk supplier
- ML score < 0.4
- Natural misspellings (indicate human, not bot)
- Unique OE content (not duplicated)

## Critical Lessons from Prior Analysis

1. **DO NOT penalize generic topic restatements in the outro field** — the question literally asks "describe what this survey was about." "Water filtration systems" is a normal answer.

2. **DO NOT penalize missing q14** — the client keeps respondents with missing q14. It's not a discard signal.

3. **DO weight first-person q14 content heavily as a KEEP signal** — any first-person content in q14 ("for my family", "my water tastes bad") is a strong protective factor.

4. **DO trust the ML triage score on boundary cases** — ML > 0.7 correlates with true discards. If ML says high risk and you see ANY other concern, lean toward discard.

5. **DO look at the CONVERGENCE of signals** — no single signal (except defender flags) is sufficient for discard. Look for 3+ converging concerns.

6. **DO consider response RELEVANCE, not just quality** — a well-written but off-topic answer is worse than a poorly-written but on-topic one.

7. **DO look at per-grid patterns** — straightlining on rating scales (q20-q24) is more common than on behavioral questions (q3-q4). Weight accordingly.

## Dataset Context
- Dataset: {dataset_name}
- Total respondents: {n_respondents}
- Matrix straightlining prevalence: {matrix_prevalence:.1%} {'(VERY HIGH — straightlining alone is NOT discriminative)' if matrix_prevalence > 0.8 else ''}
- You are reviewing chunk XX of {n_chunks}
"""


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 run_holistic_agent_review.py <xlsx_path> [--output-dir DIR] [--review-all] [--chunk-size N]")
        return

    filepath = Path(sys.argv[1])
    output_dir = None
    review_all = False
    chunk_size = 200

    for i, arg in enumerate(sys.argv[2:], 2):
        if arg == "--output-dir" and i + 1 < len(sys.argv):
            output_dir = Path(sys.argv[i + 1])
        elif arg == "--review-all":
            review_all = True
        elif arg == "--chunk-size" and i + 1 < len(sys.argv):
            chunk_size = int(sys.argv[i + 1])

    build_holistic_review_packets(filepath, output_dir or filepath.parent / "holistic_review_output", review_all, chunk_size)


if __name__ == "__main__":
    main()
