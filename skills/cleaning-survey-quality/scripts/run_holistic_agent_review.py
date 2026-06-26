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

    return f"""# Holistic Agent Review Instructions — Evidence Family Framework (v4)

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

## CORE FRAMEWORK: Evidence Families, Not Labels

Signals are not labels. They are evidence. The decision to discard should come from the convergence of independent evidence families, not from any single label.

### The Master Rule

**A row is discard-like when the core open end fails its question role, lacks grounded chain evidence, and converges with at least one independent risk family.**

The five independent risk families are:
1. **Model risk** — ML triage score >= 0.7
2. **Platform risk** — TERMFLAGS=1, qc flag, RD_Search elevated, non-English
3. **Source risk** — high supplier reject rate, elevated RD_Search threat
4. **Duplicate semantics** — text similarity to other respondents, paraphrase clusters
5. **Weak outro behavior** — generic praise, off-topic, incoherent, or chain-inconsistent outro

When the core OE fails its role AND one risk family fires, that is a discard. When the core OE is grounded and specific, it takes multiple risk families to override it.

---

## Evidence Family 1: Core Open-End Quality (THE ANCHOR)

The core open-end field is the most important signal. For each dataset, identify which OE field is the "core" field — the one that asks for personal motivation, experience, or job role. Read the question text to determine this.

### 1A. Answer-Role Test

Does the answer actually answer the question that was asked?

For a purchase-motivation question ("What prompted you to decide to buy?"):
- **FAILS the role**: "Water filtration systems" (names the topic, not a motivation), "Health concerns, improving water taste, reducing contaminants" (category language, not a personal reason), "It's essential" (not a motivation at all)
- **PASSES the role**: "My water started smelling like chlorine after the city changed treatment plants" (specific personal trigger), "My kids have eczema and the dermatologist recommended a shower filter" (specific health-driven motivation)

For a job-role question ("Tell me about your primary job"):
- **FAILS the role**: "Construction" (names the industry, not the job), "Hard work" (not a job description)
- **PASSES the role**: "I'm a licensed plumber working for a family-owned business in Philadelphia, mostly doing residential repipes" (specific trade, location, work context)

**An answer that names the topic but fails the question's role is a FAILED core OE.** This is the single most important test.

### 1B. Grounded First-Person Test

First-person pronouns ("I", "my", "we") are NOT protective by themselves. AI-generated text uses first-person too. The test is whether the first-person content is GROUNDED in lived experience.

**Grounded evidence** connects to:
- A concrete event ("after the city changed treatment plants", "when my neighbor showed me their new system")
- A household condition ("my well water has iron staining", "our pipes are old")
- A prior answer in the chain (owns a kitchen faucet filter → q14 explains why they bought that specific type)
- A product use detail ("I change the filter every 3 months", "installed it under the sink myself")
- A sensory issue ("water tasted metallic", "skin felt dry after showering")
- A health concern ("my daughter's eczema", "doctor recommended reducing chlorine")
- A news event ("after the Flint crisis", "saw a report about forever chemicals in our city")
- A place ("in our area", "here in Phoenix where the water is very hard")
- A buying context ("was remodeling the kitchen", "moved into a new house with old pipes")

**NOT grounded** (even if first-person):
- "I was concerned about the water quality" (no concrete anchor)
- "I wanted cleaner, safer water for my family" (benefit-stack language, no lived context)
- "I decided to buy a water filtration device to improve the taste and quality of my tap water" (product-description register, no personal event)

### 1C. Synthetic Detail Detection

Some details SOUND specific but are actually common synthetic detail clusters. These appear across many respondents and are template-like:

**Common synthetic detail clusters** (treat as suspicious when they appear without unusual grounding):
- "my skin" / "my hair" / "my family" — these are the most common fake specifics
- "chlorine" / "contaminants" / "hard water" — product-category vocabulary, not personal discovery
- "safer" / "cleaner" / "better-tasting" — benefit-stack language

**Genuinely specific details** (harder to fabricate):
- Named conditions: "eczema", "psoriasis", "dermatitis" (not just "skin")
- Named events: "Flint", "city changed treatment", "neighbor's new system" (not just "concerns")
- Named places: "Phoenix", "our area in Texas", "the house we just bought" (not just "my home")
- Unusual sensory details: "smelled like rotten eggs", "left orange stains in the toilet" (not just "bad taste")
- Specific product interactions: "the PUR filter kept clogging", "I compared Brita vs iSpring" (not just "wanted a filter")

**The test**: Is this detail UNUSUAL? Could 50 other respondents independently write the same thing? If yes, it's probably synthetic. If the detail is idiosyncratic — a specific brand comparison, a specific city, a specific event — it's more likely genuine.

### 1D. Product-Copy Register

Some answers sound like marketing copy rather than respondent memory. Look for:
- Benefit-stack language: "reducing contaminants", "improving water taste", "health and safety", "multi-stage filtration", "residential filtration products"
- Feature-list language: "contaminant removal technologies", "mineral buildup prevention", "advanced filtration"
- Formal sentence structure: "The benefits should be considered first before to buy", "Practically, the convenience of having clean water..."
- **This is STRONGER when the answer has no lived context** — no personal event, no sensory detail, no chain reference

### 1E. Paraphrase-Level Duplicate Detection

The `ai_text_suspicion` field detects exact/near-exact text similarity. But also check for PARAPHRASE clusters — respondents who tell the same story with different words:
- "concerned about water quality" / "wanted safer drinking water" / "remove contaminants for family" — these are the SAME story frame with different surface text
- "improve taste and safety" / "cleaner water for my family" / "healthier water for daily use" — same benefit-stack, different word order
- If the answer could be a paraphrase of 10+ other answers, it's a paraphrase cluster member

**When q14 itself is in a paraphrase cluster** (not just outro), this is a strong discard signal — the respondent is using a template with minor word variation.

---

## Evidence Family 2: Platform Risk

Read the `defender_summary` field FIRST. It consolidates all platform signals.

### Platform signals:
- **TERMFLAGS=1**: Platform fraud flag. STRONG signal (score -0.7). Override test: upgrade to REVIEW (-0.2) ONLY when the core OE has unusually strong human evidence — a specific named event, named place, named condition, or chain-consistent detail that would be very hard to fabricate. A merely first-person or generic answer does NOT override TERMFLAGS. The client overrides in ~25% of cases, but only for genuinely specific respondents.
- **qc=8 or qc=9**: RD /SEARCH threat or duplicate rejection — AUTOMATIC DISCARD (-1.0)
- **qc=6**: RD /REVIEW rejection — strong discard
- **qc=7**: OE screening failure — strong concern (the platform's own OE quality check failed)
- **qc=11**: Speeder — moderate concern
- **qc=2,4,5**: State/region/age mismatch — strong concern
- **RD_Search threat score**: >=25 = elevated, >=20 = moderate
- **Non-English language**: Automatic discard for US surveys
- **LangAssess read_level**: >=17 = very high (AI suspicion), >=15 with short text = AI suspicion, <2 with long text = incoherence

### TERMFLAGS override logic (IMPORTANT):
TERMFLAGS=1 is strong (-0.7) but NOT automatic. The override test is strict:
- **Override to REVIEW** only if: the core OE contains a specific named event/place/condition AND the answer is chain-consistent AND there are no other risk families firing. Example: "After the news about forever chemicals in our city water supply" + chain shows awareness of specific filter types + no AI markers.
- **Do NOT override** if: the core OE is first-person but generic ("I wanted cleaner water for my family"), or if AI markers are present, or if ML >= 0.7, or if the outro is generic praise. A typo does NOT qualify as "unusually strong human evidence."

---

## Evidence Family 3: Model Risk

- **ML >= 0.8**: Very high. Almost always right. If the core OE also fails its role, this is a discard. If the core OE is grounded and specific, cap at REVIEW.
- **ML >= 0.7**: High risk. If the core OE fails its role OR is generic first-person, this is a discard. If the core OE is grounded and specific with no other concerns, cap at REVIEW.
- **ML 0.5-0.7**: Ambiguous. Use as a tiebreaker — if any other risk family fires, lean toward discard.
- **ML < 0.4**: Low risk. Protective factor, but does NOT override a failed core OE if other risk families fire.

---

## Evidence Family 4: Source Risk

- **Supplier reject_rate > 30%**: High risk. Multiplier on other signals.
- **Supplier reject_rate > 20%**: Medium risk.
- **RD_Search threat >= 20**: Moderate source risk.
- **RD_Search threat >= 25**: Elevated source risk.
- Source risk alone is NOT sufficient for discard. It is a multiplier.

---

## Evidence Family 5: Duplicate Semantics

- **`ai_text_suspicion` on core OE field (e.g., q14)**: STRONG signal. The core OE text is similar to other respondents — likely templated.
- **`ai_text_suspicion` on outro ONLY**: DOWNWEIGHT. Generic topic restatements trigger high similarity because many respondents write the same thing. This is topical inevitability. BUT: outro similarity + weak core OE + any risk family = meaningful concern.
- **`oe_duplicate_counts`**: High count (>10) on personal/unusual text = very suspicious. High count on generic text = topical inevitability.
- **Paraphrase clusters**: Check manually — does the core OE tell the same story frame as many others, even with different words?

### Outro-only guardrail:
Outro similarity alone should NOT discard. But outro similarity PLUS any of these should become meaningful:
- Weak core OE (fails role test or is generic first-person)
- Platform risk (TERMFLAGS, RD_Search elevated)
- Source risk (high supplier reject rate)
- Model risk (ML >= 0.6)
- Semantic role mismatch in core OE

---

## Evidence Family 6: Weak Outro Behavior

The outro field asks "describe what this survey was about." Evaluate outro quality:
- **Generic topic restatement** ("water filtration systems", "water filter survey") = NORMAL, not a signal
- **Generic praise** ("Very good and wonderful", "Nice survey", "Great experience", "easy and fast") = mild concern. Combined with weak core OE + any risk family = contributes to discard.
- **Off-topic** ("good night my friend", "american whiskey", "customer rewards") = strong concern
- **Gibberish** = strong concern
- **Chain-inconsistent** (q14 gives a serious purchase reason but outro is generic praise or off-topic) = the combination lowers confidence in the core OE

### Open-end chain consistency:
Each open end should be evaluated against the full response chain. If q14 gives a serious, specific purchase reason but the outro is generic praise or off-topic, that combination should lower confidence. A genuine respondent who writes a detailed motivation should also be able to describe what the survey was about.

---

## Evidence Family 7: Timing & Engagement

- **bottom_10% timing**: Very fast. Concern, but not sufficient alone.
- **bottom_25% timing**: Fast. Mild concern.
- **above_median timing**: Protective factor.
- **Very fast + failed core OE + any risk family** = converging concerns → discard
- **Straightlining**: If prevalence is >80% (see dataset context), straightlining alone is NOT discriminative. Only matters when combined with other signals.

---

## The Decision Algorithm

For each respondent, work through these steps:

### Step 1: Read defender_summary
Are any platform signals firing? Note which ones.

### Step 2: Identify the core OE field
Which open-end field asks for personal motivation/experience/job role? Read its question text.

### Step 3: Apply the Answer-Role Test to the core OE
Does the answer actually answer the question? Or does it name the topic / use category language / give a non-motivation?

### Step 4: Apply the Grounded First-Person Test
If first-person, is it grounded in concrete lived experience? Or is it generic first-person with no anchor?

### Step 5: Check for synthetic details
Are the "specific" details actually common synthetic clusters ("my skin", "my family", "chlorine")? Or are they idiosyncratic (named events, named places, unusual sensory details)?

### Step 6: Check for product-copy register
Does the answer sound like marketing copy? Benefit-stack language? Feature lists?

### Step 7: Check ai_text_suspicion
Is the core OE field flagged? (Strong.) Is only outro flagged? (Downweight, but check guardrail.)

### Step 8: Check ML score
Is ML >= 0.7? >= 0.8?

### Step 9: Check chain consistency
Does the core OE fit with the rest of the answer chain? Would a genuine respondent with this motivation also give these other answers?

### Step 10: Count independent risk families
How many of the 5 risk families are firing? (Model, Platform, Source, Duplicate, Weak Outro)

### Step 11: Decide

**DISCARD** (score < -0.3) when:
- Core OE fails its role AND >= 1 risk family fires
- Core OE is generic first-person (not grounded) AND >= 1 risk family fires
- Core OE is a short non-answer (<25 chars, not a real motivation) AND >= 1 risk family fires
- TERMFLAGS=1 AND core OE is not unusually specifically grounded
- ML >= 0.8 AND core OE fails role or is generic
- Core OE has AI markers (formal adverbs, markdown, product-copy) AND ML >= 0.7
- Core OE is in a paraphrase cluster AND ML >= 0.6
- Both core OE and outro are off-topic/gibberish

**REVIEW** (score -0.3 to 0) when:
- Core OE is grounded but one risk family fires
- TERMFLAGS=1 AND core OE has unusually strong human evidence
- ML >= 0.7 AND core OE is grounded and specific with no other concerns
- Outro is generic praise + core OE is generic first-person (no risk family, but quality concern)
- Mixed signals where neither KEEP nor DISCARD is clearly warranted

**KEEP** (score > 0) when:
- Core OE passes the answer-role test AND is grounded with idiosyncratic detail AND no risk family fires
- Core OE is specific and chain-consistent AND ML < 0.5 AND no platform flags
- The answer contains unusual lived detail that would be very hard to fabricate (specific brand comparison, specific city + water problem, specific health condition + doctor recommendation)

### Typo rule:
Typos are NOT protective unless the surrounding answer is grounded and coherent. A typo inside generic content is neutral or mildly suspicious. "I was concerned about the filteration" with no other detail = not protective. "The filteration left orange stains in my toilet bowl" with a specific sensory detail = the typo is a minor human marker, but the specificity is what matters.

### Short non-answer rule:
Short answers (<25 chars) to a motivation question are almost always role failures. "It's essential", "Because I need one", "I needed an upgrade", "Samsung", "iSpring" are NOT motivations. When paired with ANY risk family signal (ML >= 0.6, RD_Search >= 20, fast timing, generic outro, high supplier risk), this becomes a discard.

### Accepted-row similarity guardrail:
Before discarding, ask: what makes this row different from accepted rows with the same surface flaw? If many client-kept respondents also wrote generic first-person q14 with ML ~0.5, then a generic first-person q14 with ML ~0.5 should NOT be discarded unless there is an additional differentiating signal. The discard should come from the CONVERGENCE of failed core OE + risk family, not from any single signal that is common among accepted rows.

### Hidden-client-signal approximation:
Rows with missing core OE but client discard likely reflect signals outside the workbook (panel history, cross-survey fraud). Approximate with combinations: missing core open end + source risk + platform risk + RD risk + weak routing + low chain substance. If multiple of these converge, lean toward REVIEW even without a clear OE failure.

---

## Platform Signal Reference

- `defender_signals.qc_flag`: 1=Not select 3, 2=State mismatch, 3=Red Herring, 4=REGION mismatch, 5=AGE mismatch, 6=RD /REVIEW rejection, 7=OE screening, 8=RD /SEARCH threat, 9=RD /SEARCH duplicate, 10=RD /SEARCH country, 11=Speeder, 12=Exceeded terms
- `defender_signals.TERMFLAGS`: 1 = platform fraud flag (strong, not automatic)
- `defender_signals.RD_Searchr1`: Threat score (0-30+)
- `defender_signals.RD_Searchr3`: Country detected
- `defender_signals.outroR1_RD_Reviewr0`: Language detected
- `defender_signals.outroR1_RD_Reviewr3`: Outro composite score (>=10 = HIGH)
- `defender_signals.lang_assess.read_level`: Flesch-Kincaid grade level
- `ai_text_suspicion.score`: 0-1 cross-respondent similarity
- `ai_text_suspicion.fields_flagged`: Which OE fields are similar to others

## Dataset Context
- Dataset: {dataset_name}
- Total respondents: {n_respondents}
- Matrix straightlining prevalence: {matrix_prevalence:.1%} {'(VERY HIGH — straightlining alone is NOT discriminative)' if matrix_prevalence > 0.8 else ''}
- You are reviewing chunk XX of {n_chunks}
- NOTE: This dataset may not be about water filtration. Read the question text in each OE field to identify the survey topic and the core OE field. Adapt the answer-role test to the actual question being asked.
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
