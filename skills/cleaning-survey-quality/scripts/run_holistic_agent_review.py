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
    """Extract ALL survey defender / quality control / platform signals.
    
    Returns dict with raw signals + a human-readable summary string.
    """
    signals = {}
    summary_parts = []

    # === 1. QC FLAG (quality control — platform's own QC check) ===
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
            summary_parts.append(f"QC FLAG: {qc_labels.get(qc_val, qc_val)}")

    # === 2. TERMFLAGS (platform termination flag — FRAUD DETECTED) ===
    tf_idx = hidx.get("TERMFLAGS")
    if tf_idx and tf_idx < len(row):
        tf = norm(row[tf_idx])
        if tf is not None:
            signals["termflags"] = tf
            if tf != 0:
                summary_parts.append(f"TERMFLAGS={tf} (PLATFORM FRAUD FLAG — auto-discard)")

    # === 3. RD_Search (research defender — bot/fraud/threat detection) ===
    rd_search_labels = {
        "RD_Searchr0": "search_threat_potential",
        "RD_Searchr1": "search_threat_score",
        "RD_Searchr2": "search_respondent_risk",
        "RD_Searchr3": "search_country",
        "RD_Searchr4": "search_flag",
        "RD_Searchr5": "search_duplicate_potential",
        "RD_Searchr6": "search_duplicate_score",
        "RD_Searchr7": "search_duplicate_flag",
    }
    rd_values = {}
    for field, label in rd_search_labels.items():
        idx = hidx.get(field)
        if idx and idx < len(row):
            val = row[idx]
            if val is not None and val != "":
                rd_values[label] = norm(val) if not isinstance(val, str) else val
                signals[field] = rd_values[label]
    # Summarize RD_Search
    threat_score = rd_values.get("search_threat_score")
    if threat_score is not None:
        try:
            ts = int(threat_score)
            if ts >= 25:
                summary_parts.append(f"RD_Search threat score={ts} (ELEVATED)")
            elif ts >= 20:
                summary_parts.append(f"RD_Search threat score={ts} (moderate)")
        except (ValueError, TypeError):
            pass
    country = rd_values.get("search_country")
    if country and country != "United States":
        summary_parts.append(f"RD_Search country={country} (NON-US)")
    dup_pot = rd_values.get("search_duplicate_potential")
    if dup_pot and str(dup_pot).lower() not in ("low", "0", "none"):
        summary_parts.append(f"RD_Search duplicate={dup_pot}")

    # === 4. RD_GetToken (token verification / bot detection) ===
    for field in ["RD_GetTokenr0", "RD_GetTokenr1"]:
        idx = hidx.get(field)
        if idx and idx < len(row):
            val = row[idx]
            if val is not None and val != "":
                signals[field] = str(val)[:50]

    # === 5. outroR1_RD_Review (outro text review — language/paste/profanity/similarity) ===
    outro_review_labels = {
        "outroR1_RD_Reviewr0": "outro_language_detected",
        "outroR1_RD_Reviewr1": "outro_pasted_response",
        "outroR1_RD_Reviewr2": "outro_profanity_check",
        "outroR1_RD_Reviewr3": "outro_composite_score",
        "outroR1_RD_Reviewr4": "outro_similarity_flag",
    }
    outro_review = {}
    for field, label in outro_review_labels.items():
        idx = hidx.get(field)
        if idx and idx < len(row):
            val = row[idx]
            if val is not None and val != "":
                outro_review[label] = norm(val) if not isinstance(val, str) else val
                signals[field] = outro_review[label]
    # Summarize outro review
    lang = outro_review.get("outro_language_detected")
    if lang and lang != "English":
        summary_parts.append(f"Outro language={lang} (NON-ENGLISH)")
    pasted = outro_review.get("outro_pasted_response")
    if pasted and str(pasted) != "0":
        summary_parts.append(f"Outro PASTED response detected")
    profanity = outro_review.get("outro_profanity_check")
    if profanity and str(profanity) != "0":
        summary_parts.append(f"Outro profanity detected")
    composite = outro_review.get("outro_composite_score")
    if composite:
        try:
            cs = int(composite)
            if cs >= 10:
                summary_parts.append(f"Outro composite score={cs} (HIGH — suspicious)")
            elif cs >= 5:
                summary_parts.append(f"Outro composite score={cs} (moderate)")
        except (ValueError, TypeError):
            pass
    sim_flag = outro_review.get("outro_similarity_flag")
    if sim_flag and str(sim_flag) == "0":
        summary_parts.append("Outro similarity flag=0 (flagged by platform)")

    # === 6. LangAssess (readability — AI text detection proxy) ===
    lang_fields = {
        "LangAssessReadLevel": "read_level",
        "LangAssessReadEase": "read_ease",
        "LangAssessNumSen": "num_sentences",
        "LangAssessNumWords": "num_words",
        "LangAssessNumSyl": "num_syllables",
    }
    lang_vals = {}
    for field, label in lang_fields.items():
        idx = hidx.get(field)
        if idx and idx < len(row):
            val = row[idx]
            if val is not None:
                try:
                    lang_vals[label] = float(val)
                except (ValueError, TypeError):
                    lang_vals[label] = val
    signals["lang_assess"] = lang_vals
    # Summarize LangAssess — high read level with short text = possible AI
    rl = lang_vals.get("read_level")
    nw = lang_vals.get("num_words")
    if rl is not None and nw is not None:
        try:
            rl_f = float(rl)
            nw_f = float(nw)
            if rl_f >= 15 and nw_f <= 15:
                summary_parts.append(f"ReadLevel={rl_f:.1f} with only {int(nw_f)} words (VERY HIGH readability for short text — possible AI-generated)")
            elif rl_f >= 17:
                summary_parts.append(f"ReadLevel={rl_f:.1f} (VERY HIGH — possible AI-generated)")
            elif rl_f < 2 and nw_f > 5:
                summary_parts.append(f"ReadLevel={rl_f:.1f} (VERY LOW — possible incoherence)")
        except (ValueError, TypeError):
            pass

    # === 7. vlist (participant source — some sources are higher risk) ===
    vlist_idx = hidx.get("vlist")
    if vlist_idx and vlist_idx < len(row):
        vlist_val = norm(row[vlist_idx])
        if vlist_val is not None:
            signals["vlist"] = vlist_val

    # === 8. decLang (declared language) ===
    decLang_idx = hidx.get("decLang")
    if decLang_idx and decLang_idx < len(row):
        dl = row[decLang_idx]
        if dl is not None and str(dl).strip():
            signals["decLang"] = str(dl).strip()
            if str(dl).strip().lower() not in ("english", "en", "us"):
                summary_parts.append(f"Declared language={dl} (NON-ENGLISH)")

    # === 9. vdropout (last seen question — detects dropouts/partials) ===
    vdropout_idx = hidx.get("vdropout")
    if vdropout_idx and vdropout_idx < len(row):
        vd = row[vdropout_idx]
        if vd is not None and str(vd).strip():
            signals["vdropout"] = str(vd).strip()

    # === 10. IP / UserAgent duplicates (detected elsewhere, but noted here) ===
    # These are computed in the cross-respondent section

    # Build the summary string
    if not summary_parts:
        signals["defender_summary"] = "No platform defender signals triggered."
    else:
        signals["defender_summary"] = " | ".join(summary_parts)

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

    # === Cross-respondent text similarity detection ("too clean to be real" pattern) ===
    # Detect AI-generated text by finding clusters of respondents whose OE answers
    # share suspiciously similar phrasing, vocabulary, and sentence structure.
    # Real humans write differently from each other; AI-generated respondents use
    # templates with minor variations.
    print(f"\n  Computing cross-respondent text similarity (AI template detection)...")
    from difflib import SequenceMatcher

    # For each OE field, compute pairwise similarity for all respondents
    # Then flag respondents whose text is >60% similar to 5+ others
    oe_similarity = {}  # rid -> {field: {"max_similarity": float, "n_similar": int, "similar_to": [rids]}}
    for i, h in oe_cols:
        field = str(h)
        texts = []  # (rid, text)
        for idx_row, row in enumerate(rows_raw):
            if i < len(row):
                val = clean(row[i])
                if val and len(val.strip()) > 20:  # Only compare substantive text
                    rid = df.iloc[idx_row]["respondent_id"] if idx_row < len(df) else str(idx_row)
                    texts.append((rid, val.strip().lower()))

        if len(texts) < 10:
            continue

        # Compute pairwise similarity (sample if too many to avoid O(n^2) blowup)
        # For >500 texts, use a sampling approach: compare each text to a random sample
        import random
        random.seed(42)
        sample_size = min(len(texts), 300)

        for rid_a, text_a in texts:
            if rid_a not in oe_similarity:
                oe_similarity[rid_a] = {}
            if field not in oe_similarity[rid_a]:
                oe_similarity[rid_a][field] = {"max_similarity": 0, "n_similar": 0, "similar_to": []}

            # Compare to a sample of other texts
            others = [t for t in texts if t[0] != rid_a]
            if len(others) > sample_size:
                others = random.sample(others, sample_size)

            n_similar = 0
            max_sim = 0
            similar_to = []
            for rid_b, text_b in others:
                sim = SequenceMatcher(None, text_a, text_b, autojunk=False).ratio()
                if sim > max_sim:
                    max_sim = sim
                if sim > 0.6:
                    n_similar += 1
                    if len(similar_to) < 5:
                        similar_to.append(rid_b)

            oe_similarity[rid_a][field]["max_similarity"] = round(max_sim, 3)
            oe_similarity[rid_a][field]["n_similar"] = n_similar
            oe_similarity[rid_a][field]["similar_to"] = similar_to

    # Compute AI-text suspicion score per respondent
    # High similarity to many others = likely from a template = AI-generated
    ai_suspicion = {}  # rid -> {"score": 0-1, "fields_flagged": [...], "details": str}
    for rid, fields in oe_similarity.items():
        flagged = []
        max_n_similar = 0
        max_sim = 0
        for field, info in fields.items():
            if info["n_similar"] >= 5 or info["max_similarity"] > 0.8:
                flagged.append(field)
                max_n_similar = max(max_n_similar, info["n_similar"])
                max_sim = max(max_sim, info["max_similarity"])

        if flagged:
            # Score: more fields flagged + higher similarity = higher suspicion
            score = min(1.0, (len(flagged) * 0.3) + (max_n_similar * 0.05) + (max_sim * 0.2))
            detail_parts = []
            for field in flagged:
                info = fields[field]
                detail_parts.append(f"{field}: {info['n_similar']} similar (max={info['max_similarity']})")
            ai_suspicion[rid] = {
                "score": round(score, 3),
                "fields_flagged": flagged,
                "details": " | ".join(detail_parts),
            }

    n_ai_flagged = len(ai_suspicion)
    print(f"    AI text suspicion: {n_ai_flagged} respondents flagged ({n_ai_flagged/len(df)*100:.1f}%)")

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

        # Defender signals (includes defender_summary string)
        defender = get_defender_signals(raw_row, hidx)

        # AI text suspicion (cross-respondent similarity)
        ai_info = ai_suspicion.get(rid, {"score": 0, "fields_flagged": [], "details": ""})

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
            "defender_summary": defender.get("defender_summary", "No platform defender signals triggered."),
            "ai_text_suspicion": ai_info,
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

### 4. Survey Defender Signals (ALL platform signals — read the defender_summary field)
Each packet has a `defender_summary` field that consolidates ALL platform/research defender signals into a human-readable string. READ THIS FIRST — it tells you which platform flags fired.

**Platform signals included in defender_summary:**
- `defender_signals.qc_flag`: If non-zero, the platform already flagged this respondent
  - qc=6 (RD /REVIEW rejection), qc=8 (SEARCH threat), qc=9 (SEARCH duplicate) = STRONG discard
  - qc=11 (Speeder) = moderate concern
  - qc=2,4,5 (state/region/age mismatch) = strong concern
  - qc=7 (OE screening) = strong concern (open-end failed quality check)
- `defender_signals.TERMFLAGS`: Non-zero = **PLATFORM FRAUD FLAG — AUTO-DISCARD, full stop.**
  The platform's own fraud detector flagged this respondent. Do NOT let first-person q14 content override this. TERMFLAGS=1 means the platform already determined this is fraud. Treat it as an automatic discard regardless of any other signal.
- `defender_signals.RD_Searchr1`: Research Defender threat score (0-30+)
  - >=25 = ELEVATED (strong concern)
  - >=20 = moderate concern
  - <20 = low (normal for most respondents)
- `defender_signals.RD_Searchr3`: Country detected — if not "United States", concerning for US survey
- `defender_signals.outroR1_RD_Reviewr0`: Language detected in outro — if not "English", concerning
- `defender_signals.outroR1_RD_Reviewr1`: Pasted response detected in outro
- `defender_signals.outroR1_RD_Reviewr3`: Outro composite score (0-17+) — >=10 = HIGH suspicion
- `defender_signals.outroR1_RD_Reviewr4`: Outro similarity flag — 0 = flagged by platform
- `defender_signals.lang_assess.read_level`: Flesch-Kincaid reading level
  - >=15 with short text = possible AI-generated (too sophisticated for typical respondent)
  - >=17 = VERY HIGH — strong AI suspicion
  - <2 with long text = possible incoherence
- `defender_signals.decLang`: Declared language — if not English, concerning
- `defender_signals.vlist`: Participant source (supplier list ID)
- `defender_signals.vdropout`: Last seen question — detects dropouts/partials

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

### 10. AI-Generated Text Detection (CRITICAL — this is what we're missing)
The client's human reviewers can spot AI-generated text that reads as "genuine" to our semantic classifier. We now detect this with two approaches:

**A. Cross-respondent text similarity (`ai_text_suspicion` field):**
- `ai_text_suspicion.score`: 0-1, how likely the text is AI-generated based on template matching
- `ai_text_suspicion.fields_flagged`: Which OE fields have suspicious similarity to other respondents
- `ai_text_suspicion.details`: Specific similarity metrics
- **score >= 0.5** = STRONG concern — this respondent's text is suspiciously similar to many others
- **score >= 0.3** = moderate concern — some similarity detected
- The key insight: when 50 respondents all write "I decided to buy a water filtration device to improve the taste and quality of my tap water," that's NOT 50 independent humans. That's a template. Real humans write differently from each other.

**B. AI text pattern recognition (evaluate in the OE text itself):**
Look for these AI-generation markers in the open-end responses:
- **Formal adverbs at sentence start**: "Notably,", "Without a doubt,", "Practically,", "Honestly,", "Importantly," — real respondents rarely write this way
- **Markdown formatting**: Bold text (**like this**), bullet points, or numbered lists in OE fields — bots copy formatted text
- **Perfect grammar with uniform vocabulary**: If the q14 uses words like "contaminants," "chlorine," "safer," "cleaner" in perfect sentences — check if many other respondents use the EXACT same vocabulary
- **Overly structured responses**: "First, ... Second, ... Finally, ..." or "The primary driver is..." — survey respondents don't write essays
- **Third-person generalizing**: "People want...", "Consumers base their decisions on..." — describing market behavior, not personal experience
- **Product-description language**: Text that reads like marketing copy ("multi-stage filtration," "contaminant removal technologies") rather than personal motivation

**When AI suspicion is HIGH (score >= 0.5 OR multiple AI markers present):**
- This is a STRONG discard signal, even if the text reads as first-person and on-topic
- The client discards these respondents — they can spot the uncanny valley
- Combine with ML score: if ML >= 0.6 AND ai_text_suspicion >= 0.3, lean toward DISCARD
- Do NOT let "first-person q14" override AI suspicion — AI-generated first-person text is still fraud

## Scoring Decision Framework

### AUTOMATIC DISCARD (score -1.0, no exceptions):
- **TERMFLAGS=1**: The platform's fraud detector flagged this respondent. DISCARD regardless of any other signal. Do NOT let first-person q14 content, long completion time, or any other "good" signal override this. The platform has more data than we do (panel history, IP analysis, digital fingerprint). If TERMFLAGS=1, it's fraud.
- **qc=8 or qc=9**: RD /SEARCH threat or duplicate rejection — platform already rejected this respondent
- **Non-English language in US survey**: outroR1_RD_Reviewr0 != "English" or decLang != English

### Strong DISCARD signals (score -0.7 to -1.0):
- Defender flag (qc=6,8,9) + any other concern
- **AI text suspicion score >= 0.5** — text is template-generated, not human
- **AI text markers present** (formal adverbs, markdown, perfect uniform grammar) + ML >= 0.6
- Gibberish or off-topic in q14 + off-topic outro
- Off-topic outro + straightlining across most grids + very fast
- Duplicated personal story (same q14 text as many others)
- TERMFLAGS=1 (already covered above, but reinforcing)

### Moderate DISCARD signals (score -0.3 to -0.5):
- **AI text suspicion score 0.3-0.5** + ML >= 0.6 — suspicious similarity but not definitive
- **AI text markers present** (formal adverbs, product-description language) without other signals
- Off-topic outro with no personal q14 but some answer variation
- Generic praise outro + very fast + straightlining
- Elevated RD_Search threat score (>=20) + generic OE
- High-risk supplier + multiple converging concerns
- Third-person generalizing in q14 ("People want...", "Consumers base...")

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

3. **DO weight first-person q14 content heavily as a KEEP signal** — any first-person content in q14 ("for my family", "my water tastes bad") is a strong protective factor. **BUT**: if `ai_text_suspicion.score >= 0.5` or AI markers are present (formal adverbs, markdown, perfect uniform grammar), the first-person content may be AI-generated. In that case, it is NOT a protective factor — it's fraud.

4. **DO trust the ML triage score on boundary cases** — ML > 0.7 correlates with true discards. If ML says high risk and you see ANY other concern, lean toward discard.

5. **DO look at the CONVERGENCE of signals** — no single signal (except TERMFLAGS and qc=8/9) is sufficient for discard. Look for 3+ converging concerns.

6. **DO consider response RELEVANCE, not just quality** — a well-written but off-topic answer is worse than a poorly-written but on-topic one.

7. **DO look at per-grid patterns** — straightlining on rating scales (q20-q24) is more common than on behavioral questions (q3-q4). Weight accordingly.

8. **DO treat TERMFLAGS=1 as an automatic discard** — the platform's fraud detector has access to panel history, IP analysis, and digital fingerprinting that we don't have. If it flagged this respondent, trust it. Do NOT override with "but the q14 looks first-person." AI-generated first-person text is still fraud.

9. **DO read the `defender_summary` field FIRST** — it consolidates all platform signals into one string. If it says anything other than "No platform defender signals triggered," pay attention. The platform has signals we can't see from the Excel alone.

10. **DO check `ai_text_suspicion` for every respondent** — if the score is >= 0.3, the respondent's text is suspiciously similar to other respondents. This is the "too clean to be real" pattern: when many respondents write the same way, they're using a template, not writing independently. This is the #1 thing we were missing — the client catches AI-generated text that our semantic classifier reads as genuine.

11. **DO look for AI text markers in the OE text itself**: formal adverbs ("Notably," "Without a doubt," "Practically"), markdown formatting (**bold**), product-description language ("multi-stage filtration," "contaminant removal technologies"), and overly structured responses. Real survey respondents don't write essays or marketing copy.

12. **DO remember that the client has signals we don't have** — panel history, cross-survey fraud detection, IP/digital fingerprint analysis. Some respondents with ML=0.17 and 26-minute completion times are still discarded by the client. That decision is based on data outside this workbook. We can only approximate it with the signals we have (TERMFLAGS, RD_Search, AI text detection). When in doubt, trust the platform signals.

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
