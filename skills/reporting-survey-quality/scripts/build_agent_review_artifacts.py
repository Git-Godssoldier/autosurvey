#!/usr/bin/env python3
"""Build reusable agent review artifacts from scorer output and full-row audit."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


SUBSTANTIVE_TERMS = re.compile(
    r"cost|price|quality|durab|fit|function|feature|design|style|brand|safety|security|privacy|"
    r"comfort|convenien|easy|efficient|energy|warrant|service|support|install|maintain|material|"
    r"performance|availability|inventory|stock|trust|recommend|contract|construction|repair|project|"
    r"home|store|supplier|digital|software|tool|app|online|order|ordering|delivery|schedule|"
    r"scheduling|communication|workflow|payment|invoice|estimate|bid|proposal|pricing|discount|"
    r"deal|purchase|checkout|fee|fees|client|customer|labor|worker|blueprint|takeoff|job",
    re.I,
)
CATEGORY_CONTEXT_TERMS = re.compile(
    r"gas|fuel|pump|station|convenience|store|racetrac|raceway|7-eleven|circle k|quiktrip|\\bqt\\b|wawa|"
    r"speedway|casey|murphy|food|drink|coffee|snack|slurpee|bathroom|restroom|parking|clean|staff|"
    r"employee|cashier|receipt|reward|loyalty|app|checkout|price|cheap|cheaper|deal|inside|road|visit|"
    r"padlock|keyed|lock|locked|locking|security|gate|facility|equipment|storage|toolbox|tool box|tools|"
    r"jobsite|worksite|construction site|warehouse|wherehouse|office|room|entrance|door|trailer|cabinet|"
    r"drawer|safe|cage|shed|garage|locker|fence|chain|access|pharmacy|parking lot|dumpster|building|shop|"
    r"rust|weather|shackle|keyway|steel|brass|outdoor|marine|body cover|vault|mailbox|electrical|device|"
    r"utilities|utility|property|intruder|medication|basement|school|plant|club ?house|corporate|garbage|"
    r"wet area|all over|everywhere|licker|liquor|file|desk|drawers",
    re.I,
)
PROJECT_ANSWER_TERMS = re.compile(
    r"paint|painting|repaint|floor|flooring|tile|kitchen|bedroom|bathroom|basement|porch|deck|gazebo|"
    r"fireplace|fire place|driveway|sidewalk|patio|padio|pool|pond|cabinet|countertop|sink|stove|"
    r"microwave|appliance|renovat|remodel|replace|replacing|redo|built|building|added|extending|room|"
    r"outdoor|garden|barbecue|bbq|wood|concrete|paving|front porch|interior",
    re.I,
)
ENTHUSIASM_TERMS = re.compile(
    r"love|loved|like|liked|great|excellent|awesome|amazing|good|nice|interesting|helpful|perfect|best|"
    r"excited|enthusiastic|yes|wow|cool",
    re.I,
)
NON_RESPONSE_TERMS = re.compile(
    r"^(na|n/a|none|nothing|no comment|dont know|don't know|no idea|not sure|asdf|qwerty|test)$",
    re.I,
)
ABUSIVE_OR_HOSTILE_TERMS = re.compile(r"fuck|shit|piece[s]? of shit", re.I)
PLACEHOLDER_FRAGMENT_RE = re.compile(
    r"\b(?:test|asdf|qwerty|n/?a|dont know|don't know|no idea|not sure)\b",
    re.I,
)
CONTACT_OR_MISPLACED_TEXT_RE = re.compile(
    r"\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b|\b\d{3,5}\s+[A-Za-z0-9 .'-]+(?:rd|road|st|street|ave|avenue|dr|drive|ln|lane|blvd|boulevard)\b|"
    r"\bgood morning my love\b|\bsend me a picture\b|\bthanks for the update\b",
    re.I,
)


def text(value: object, default: str = "") -> str:
    if pd.isna(value):
        return default
    return str(value).strip()


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def source_workbook(run_dir: Path) -> Path:
    summary = json.loads((run_dir / "quality_summary.json").read_text(encoding="utf-8"))
    return Path(summary["source_files"][0]["file"])


def source_sheet(run_dir: Path) -> str:
    summary = json.loads((run_dir / "quality_summary.json").read_text(encoding="utf-8"))
    return str(summary["source_files"][0].get("sheet", "A1"))


def row_from(indexed: pd.DataFrame, key: str) -> pd.Series:
    if indexed.empty or key not in indexed.index:
        return pd.Series(dtype=object)
    row = indexed.loc[key]
    if isinstance(row, pd.DataFrame):
        return row.iloc[0]
    return row


def chain_segments(full_chain: str) -> list[str]:
    return [item.strip() for item in full_chain.split("||") if item.strip()]


def chain_answer_text(full_chain: str) -> str:
    parsed = parsed_chain_segments(full_chain)
    if parsed:
        return " ".join(segment.get("answer", "") for segment in parsed)
    answers: list[str] = []
    for segment in chain_segments(full_chain):
        if ": " in segment:
            answers.append(segment.split(": ", 1)[1])
        else:
            answers.append(segment)
    return " ".join(answers)


def parsed_chain_segments(full_chain: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for segment in chain_segments(full_chain):
        match = re.match(r"([^[]+)\s+\[([^\]]+)\]\s*(.*):\s*(.*)$", segment)
        if match:
            rows.append(
                {
                    "column": match.group(1).strip(),
                    "role": match.group(2).strip(),
                    "prompt": match.group(3).strip(),
                    "answer": match.group(4).strip(),
                }
            )
    return rows


def first_chain_answer(segments: list[dict[str, str]], pattern: str) -> str:
    regex = re.compile(pattern, re.I)
    for segment in segments:
        if regex.search(segment.get("column", "")) and segment.get("answer"):
            return segment["answer"]
    return ""


def short_answer(value: str, limit: int = 170) -> str:
    clean = re.sub(r"\s+", " ", text(value))
    if len(clean) <= limit:
        return clean
    return clean[:limit].rsplit(" ", 1)[0].rstrip(" .,;:") + "..."


def chain_readout(full_chain: str) -> str:
    segments = parsed_chain_segments(full_chain)
    if not segments:
        return "The focused chain did not include readable section answers."
    parts: list[str] = []
    qcoe = first_chain_answer(segments, r"^qcoe1$")
    q9 = first_chain_answer(segments, r"^(q9|q9r10oe|PIPEINTOQ10)$")
    q10 = first_chain_answer(segments, r"^q10$")
    q43 = first_chain_answer(segments, r"^q43")
    outro = first_chain_answer(segments, r"^outro$")
    q32_count = sum(1 for segment in segments if re.match(r"q32", segment.get("column", ""), re.I))
    if qcoe:
        parts.append(f"service example: {short_answer(qcoe)}")
    if q9:
        parts.append(f"preferred store: {short_answer(q9)}")
    if q10:
        parts.append(f"reason: {short_answer(q10)}")
    if q43:
        parts.append(f"purchase behavior: {short_answer(q43)}")
    if q32_count:
        parts.append(f"Q32 had {q32_count} answered matrix fields")
    if outro:
        parts.append(f"survey recap: {short_answer(outro)}")
    if not parts:
        return "The focused chain had fields, but none gave a compact narrative answer."
    return "The focused chain showed " + "; ".join(parts[:6]) + "."


def repeated_character_expression(value: str) -> bool:
    return bool(re.search(r"([a-z!?])\1{2,}", value.lower()))


def has_substantive_context(value: str) -> bool:
    return bool(SUBSTANTIVE_TERMS.search(value))


def has_meaningful_narrative_context(value: str) -> bool:
    clean = re.sub(r"\s+", " ", value).strip()
    if not clean:
        return False
    if NON_RESPONSE_TERMS.fullmatch(clean) or PLACEHOLDER_FRAGMENT_RE.search(clean) or CONTACT_OR_MISPLACED_TEXT_RE.search(clean):
        return False
    if CATEGORY_CONTEXT_TERMS.search(clean):
        return True
    if severe_weak_narrative(clean) or gibberish_or_misplaced_text(clean):
        return False
    return bool(SUBSTANTIVE_TERMS.search(clean) or CATEGORY_CONTEXT_TERMS.search(clean))


def has_plausible_project_answer(value: str) -> bool:
    return bool(PROJECT_ANSWER_TERMS.search(value))


def has_enthusiastic_context(value: str) -> bool:
    return bool(ENTHUSIASM_TERMS.search(value))


def severe_weak_narrative(value: str) -> bool:
    clean = re.sub(r"\s+", " ", value).strip()
    if not clean:
        return True
    if NON_RESPONSE_TERMS.fullmatch(clean):
        return True
    if PLACEHOLDER_FRAGMENT_RE.search(clean) and not has_substantive_context(clean):
        return True
    words = re.findall(r"[A-Za-z0-9']+", clean)
    repeated_tokens = [word.lower() for word in words if len(word) > 2]
    if repeated_tokens:
        most_common = max(repeated_tokens.count(word) for word in set(repeated_tokens))
        if most_common >= 3 and len(set(repeated_tokens)) <= 3 and not has_substantive_context(clean):
            return True
    if re.search(r"(.)\1{4,}", clean) and not has_substantive_context(clean):
        return True
    return False


def gibberish_or_misplaced_text(value: str) -> bool:
    clean = re.sub(r"\s+", " ", value).strip()
    if not clean:
        return True
    if CONTACT_OR_MISPLACED_TEXT_RE.search(clean):
        return True
    if has_substantive_context(clean):
        return False
    words = re.findall(r"[A-Za-z0-9']+", clean)
    if not words:
        return True
    short_words = sum(1 for word in words if len(word) <= 3)
    vowel_words = sum(1 for word in words if re.search(r"[aeiouy]", word, re.I))
    if len(words) <= 6 and short_words >= max(3, len(words) - 1):
        return True
    if len(words) <= 6 and vowel_words <= max(1, len(words) // 3):
        return True
    return False


def narrative_answers_from_chain(full_chain: str) -> list[str]:
    answers: list[str] = []
    for segment in parsed_chain_segments(full_chain):
        role = segment.get("role", "")
        column = segment.get("column", "")
        if "narrative_open_end" in role or re.search(r"^(qcoe1|q10|outro)$", column, re.I):
            answer = text(segment.get("answer"))
            if answer:
                answers.append(answer)
    return answers


def semantic_verifier_profile(audit_row: pd.Series, review_row: pd.Series, raw_text: str, full_chain: str) -> dict[str, object]:
    if not full_chain:
        raise ValueError("Final agent review requires full_response_chain from the independent audit.")

    criteria = text(review_row.get("criteria_triggered"))
    narrative = text(audit_row.get("narrative_quality"))
    risks = text(audit_row.get("independent_risk_factors"))
    action = text(audit_row.get("independent_suggested_action"))
    second_pass = text(review_row.get("second_pass_decision"))
    segments = chain_segments(full_chain)
    answer_text = chain_answer_text(full_chain)
    narrative_answers = narrative_answers_from_chain(full_chain)
    narrative_answer_text = " ".join(narrative_answers)
    combined_text = f"{raw_text} {answer_text}"

    early_screening_discard = action == "review_for_possible_discard" or second_pass == "discard_candidate"
    counterevidence: list[str] = []
    discard_basis: list[str] = []
    patterns: list[str] = []
    meaningful_narratives = [item for item in narrative_answers if has_meaningful_narrative_context(item)]

    expressive_repetition = repeated_character_expression(raw_text) or repeated_character_expression(answer_text)
    if expressive_repetition:
        patterns.append("duplicate-character or repeated-punctuation expression")
        if has_enthusiastic_context(combined_text) and has_substantive_context(combined_text):
            counterevidence.append("Repeated characters appear in an enthusiastic or spirited answer with substantive context.")

    if narrative in {"topic_relevant", "substantive_narrative", "product_relevant"}:
        counterevidence.append("The audited narrative is usable in context.")
    if meaningful_narratives:
        counterevidence.append("The full response chain contains a concrete store, product, service, or evaluation answer.")
    if len(segments) >= 8:
        patterns.append(f"The verifier reviewed nonempty answers across {len(segments)} fields before judging discard.")

    if ABUSIVE_OR_HOSTILE_TERMS.search(raw_text):
        discard_basis.append("The reviewed text contains hostile or abusive language.")
    if NON_RESPONSE_TERMS.fullmatch(raw_text.strip()):
        discard_basis.append("The reviewed text is a direct non-response.")
    weak_narratives = [item for item in narrative_answers if severe_weak_narrative(item) or gibberish_or_misplaced_text(item)]
    if len(weak_narratives) >= 2 and not counterevidence:
        discard_basis.append("Multiple critical narrative answers are non-responsive, gibberish, or misplaced text.")
    if (severe_weak_narrative(raw_text) or gibberish_or_misplaced_text(raw_text)) and "speed_risk" in risks and not counterevidence:
        discard_basis.append("Speed combines with a severely weak or misplaced critical narrative answer and no full-chain counterevidence was found.")
    if "speed_risk" in risks and not meaningful_narratives and not counterevidence:
        discard_basis.append("The row was fast and the focused response chain did not contain a meaningful narrative answer.")
    if CONTACT_OR_MISPLACED_TEXT_RE.search(narrative_answer_text) and "speed_risk" in risks and not counterevidence:
        discard_basis.append("Contact information or unrelated conversational text appears in critical narrative fields during a fast complete.")
    if narrative == "nonsensical_or_repetitive" and not counterevidence:
        discard_basis.append("The narrative is nonsensical or repetitive and the full chain does not recover useful context.")
    if "narrative_discard_risk" in risks and not counterevidence:
        discard_basis.append("The audit found a narrative discard risk and the full chain did not provide a benign reading.")
    if "narrative_quality_risk" in risks and "speed_risk" in risks and severe_weak_narrative(raw_text) and not counterevidence:
        discard_basis.append("Severely weak narrative evidence combines with speed and the full chain does not recover usable context.")
    if "role_fit_risk" in risks and not counterevidence:
        discard_basis.append("Role fit appears invalid and the full chain does not provide qualifying context.")
    if "duplicate_ip" in criteria and "matrix_straightline" in criteria and not counterevidence:
        discard_basis.append("Independent duplicate evidence combines with straightlining and no full-chain counterevidence was found.")
    if "matrix_straightline" in criteria and "low_effort_open_end" in criteria and not counterevidence:
        discard_basis.append("Straightlining combines with low-effort text and no full-chain counterevidence was found.")

    if not early_screening_discard:
        final = "keep_with_review_note"
        reason = "Early screening routed the row for review, but it did not recommend discard."
    elif discard_basis:
        final = "discard"
        reason = "Full-chain review found a semantic discard basis after reading the response chain."
    else:
        final = "keep_with_review_note"
        reason = "Full-chain review did not find enough semantic evidence to support discard."

    return {
        "early_screening_discard_recommendation": early_screening_discard,
        "agent_verifier_mode": "full_chain_critic_verifier",
        "agent_final_decision": final,
        "verifier_reason": reason,
        "verifier_counterevidence": " ".join(counterevidence) if counterevidence else "No strong semantic counterevidence found.",
        "semantic_discard_basis": " ".join(discard_basis) if discard_basis else "No semantic discard basis found after full-chain review.",
        "semantic_pattern_findings": " ".join(patterns) if patterns else "No special semantic expression pattern found.",
    }


def review_theme(key: str, audit_row: pd.Series, review_row: pd.Series) -> str:
    criteria = text(review_row.get("criteria_triggered"))
    narrative = text(audit_row.get("narrative_quality"))
    risks = text(audit_row.get("independent_risk_factors"))
    action = text(audit_row.get("independent_suggested_action"))
    second_pass = text(review_row.get("second_pass_decision"))

    if action == "review_for_possible_discard" or second_pass == "discard_candidate":
        if narrative == "nonsensical_or_repetitive":
            return "repetitive or nonsensical narrative discard candidate"
        if "narrative_quality_risk" in risks and "speed_risk" in risks:
            return "speed plus weak or evasive narrative discard candidate"
        if "duplicate_ip" in criteria and "matrix_straightline" in criteria:
            return "independent duplicate cluster plus straightline discard candidate"
        if "duplicate_ip" in criteria and "raw_qtime_under_4_minutes" in criteria:
            return "independent duplicate cluster plus speed discard candidate"
        if "matrix_straightline" in criteria:
            return "straightline plus weak evidence discard candidate"
        if "role_fit_risk" in risks:
            return "role-fit risk discard candidate"
        if "brand_answer_risk" in risks:
            return "brand answer risk discard candidate"
        if "duplicate_ip_risk" in risks:
            return "independent duplicate cluster discard candidate"
        return "non-cooperative or evasive narrative discard candidate"

    if "raw_qtime_under_4_minutes" in criteria and narrative in {"topic_relevant", "substantive_narrative", "product_relevant"}:
        return "speed-only plausible narrative answer kept with note"
    if narrative == "generic_survey_feedback":
        return "generic survey-feedback narrative kept for PM calibration"
    if narrative in {"low_information", "unclear_product_answer"}:
        raw = text(audit_row.get("narrative_text")).lower()
        factor_terms = [
            "cost",
            "price",
            "quality",
            "fit",
            "function",
            "warranty",
            "strength",
            "durability",
            "comfort",
            "visibility",
            "service",
            "brand",
            "design",
            "safety",
            "security",
            "privacy",
            "easy",
            "convenience",
        ]
        if any(term in raw for term in factor_terms):
            return "thin but topic-adjacent narrative kept for PM calibration"
        return "weak or unclear narrative kept for PM calibration"
    if "open_end_topic_mismatch" in criteria and narrative in {"topic_relevant", "substantive_narrative", "product_relevant"}:
        return "topic-adjacent keyword false positive on narrative text"
    if "duplicate" in criteria:
        return "technical duplicate cluster kept for PM context"
    if "low_effort" in criteria:
        return "weak or unclear narrative kept for PM calibration"
    return "general review signal kept for PM calibration"


def verified_theme(theme: str, decision: str) -> str:
    if decision != "discard" and "discard candidate" in theme:
        return theme.replace("discard candidate", "kept after critic verification")
    return theme


def semantic_judgment(key: str, decision: str, theme: str, raw_text: str, full_chain: str, audit_row: pd.Series, verifier: dict[str, object]) -> str:
    narrative = text(audit_row.get("narrative_quality"), "not_classified")
    risks = text(audit_row.get("independent_risk_factors"), "none")
    chain_note = chain_readout(full_chain)
    if decision == "discard":
        return (
            f"We recommend respondent {key} for exclusion review. The final theme is {theme}. "
            f"The basis is: {verifier['semantic_discard_basis']} "
            f"{chain_note} Narrative class: {narrative}. Risk factors: {risks}."
        )
    return (
        f"Keep respondent {key} with a review note. The final theme is {theme}. "
        f"The scoring layer routed the row for review, but the focused chain did not support exclusion. "
        f"{chain_note} Counterevidence: {verifier['verifier_counterevidence']} "
        f"Narrative class: {narrative}."
    )


def language_assessment(decision: str, raw_text: str) -> str:
    if decision == "discard":
        return "The concern is answer substance. The answer is evasive, repetitive, generic, or too weak for a required response."
    if len(raw_text.split()) <= 5:
        return "The answer is short. Keep it when the surrounding chain gives a clear reason or a valid simple factor."
    return "The language is readable enough for review. Judge it by fit to the prompt, not by polish alone."


def next_step(decision: str, theme: str) -> str:
    if decision == "discard":
        return "Escalate for PM exclusion review. Add this pattern to narrative-quality detection before the next first pass."
    if "speed-only" in theme:
        return "Keep qtime as a routing signal. Escalate speed only when it is paired with weak narrative quality or another strong signal."
    if "thin but" in theme:
        return "Ask PM whether short factor-list answers are acceptable for this field. Keep them review-only until that rule exists."
    if "survey-feedback" in theme:
        return "Classify survey-feedback wording separately from substantive answers before topic scoring."
    if "keyword false positive" in theme:
        return "Build the topic map from prompt text and sampled accepted answers before scoring topic mismatch."
    return "Use this row as PM calibration for answer depth and field role before changing scoring severity."


def synthesis_for_theme(theme: str, group: pd.DataFrame) -> dict[str, object]:
    lower = theme.lower()
    if "kept after critic verification" in lower:
        why = "Early screening suggested exclusion, but full-chain semantic review found recoverable context."
        recommendation = "Keep these cases as examples where final review must read the full response chain before excluding a respondent."
        parameter = "Early exclusion flags require full-chain semantic confirmation before removal."
    elif "weak or unclear" in lower:
        why = "Rows were weak or unclear but did not meet an automatic discard threshold without PM depth rules."
        recommendation = "Add PM examples of acceptable and unacceptable answers to the next first-pass context."
        parameter = "Weak narrative answers should remain PM calibration examples unless another strong signal appears."
    elif "speed-only plausible" in lower:
        why = "Rows completed quickly but gave plausible substantive answers."
        recommendation = "Keep qtime as a routing signal and require a weak narrative, duplicate cluster, or other quality issue before discard."
        parameter = "Speed-only rows should stay review-only."
    elif "thin but" in lower:
        why = "Rows were very short but named a plausible factor."
        recommendation = "Create a minimum-depth rule for critical narratives after PM decides whether short factor lists are acceptable."
        parameter = "Short factor answers should be review-only unless paired with another strong signal."
    elif "keyword false positive" in lower:
        why = "Rows answered the substantive prompt but used wording outside the seed topic map."
        recommendation = "Build a project-specific semantic topic map from Datamap prompts and sampled open ends before scoring topic mismatch."
        parameter = "Use keyword mismatch as review routing only until semantic relevance is confirmed."
    elif "survey-feedback" in lower:
        why = "Rows looked like feedback on the survey or idea rather than clear answers to the prompt, but did not carry enough evidence for automatic discard."
        recommendation = "Classify survey-feedback wording separately from topic relevance."
        parameter = "Survey-feedback answers should be PM calibration examples for required narrative fields."
    elif "duplicate" in lower:
        why = "Rows had a technical duplicate signal but no enough evidence for row-level discard."
        recommendation = "Review duplicate clusters with source, timing, respondent id, and answer similarity before discard."
        parameter = "Duplicate-only rows should stay review-only."
    else:
        why = "Rows had a review signal but did not create a specific discard rule."
        recommendation = "Keep this pattern as review-only until PM examples define a stronger rule."
        parameter = "Do not escalate without converging evidence."
    return {
        "theme": theme,
        "kept_review_rows": int(len(group)),
        "example_respondent_keys": ", ".join(group["respondent_key"].astype(str).head(12)),
        "why_kept": why,
        "survey_question_or_parameter_recommendation": recommendation,
        "suggested_quality_parameter": parameter,
        "issue_pattern": why,
    }


def build(run_dir: Path) -> None:
    respondent = read_csv(run_dir / "respondent_review_table.csv")
    row_scores = read_csv(run_dir / "row_scores.csv")
    audit = read_csv(run_dir / "independent_full_response_audit.csv")
    if respondent.empty:
        raise SystemExit(f"No respondent_review_table.csv found in {run_dir}")
    if audit.empty:
        raise SystemExit(f"No independent_full_response_audit.csv found in {run_dir}")
    if "full_response_chain" not in audit.columns:
        raise SystemExit("No full_response_chain column found. Rerun build_independent_full_response_audit.py before building final agent review artifacts.")

    workbook = source_workbook(run_dir)
    source = pd.read_excel(workbook, sheet_name=source_sheet(run_dir))
    key_col = "uuid" if "uuid" in source.columns else "record"
    if key_col not in source.columns:
        raise SystemExit("No respondent key column found. Expected `uuid` or `record` in the source sheet.")
    expected_rows = len(source)
    if len(audit) != expected_rows:
        raise SystemExit(
            f"Independent full-response audit row count mismatch: source has {expected_rows} rows, "
            f"but independent_full_response_audit.csv has {len(audit)} rows."
        )
    if len(respondent) != expected_rows:
        raise SystemExit(
            f"Respondent review row count mismatch: source has {expected_rows} rows, "
            f"but respondent_review_table.csv has {len(respondent)} rows."
        )
    if not row_scores.empty and len(row_scores) != expected_rows:
        raise SystemExit(
            f"Row score count mismatch: source has {expected_rows} rows, but row_scores.csv has {len(row_scores)} rows."
        )
    source_keys = set(source[key_col].astype(str))
    audit_keys_all = set(audit["respondent_key"].astype(str)) if "respondent_key" in audit.columns else set()
    missing_audit_keys = sorted(source_keys - audit_keys_all)
    if missing_audit_keys:
        preview = ", ".join(missing_audit_keys[:10])
        raise SystemExit(f"Independent full-response audit is missing source respondents: {preview}")
    nonempty_chains = audit["full_response_chain"].astype(str).str.strip().ne("").sum()
    if nonempty_chains == 0:
        raise SystemExit("Independent full-response audit contains no stitched full response chains.")
    source_index = source.set_index(key_col)
    review_index = respondent.set_index("respondent_key")
    audit_index = audit.set_index("respondent_key")

    first_pass_keys = set(respondent.loc[respondent["second_pass_decision"].astype(str).ne("keep_no_issue"), "respondent_key"].astype(str))
    audit_keys = set(audit.loc[audit["independent_suggested_action"].astype(str).ne("keep_no_issue_from_independent_audit"), "respondent_key"].astype(str))
    review_keys = sorted(first_pass_keys | audit_keys)

    rows: list[dict[str, object]] = []
    for key in review_keys:
        sr = row_from(source_index, key)
        rr = row_from(review_index, key)
        ar = row_from(audit_index, key)
        raw_text = text(ar.get("narrative_text")) or text(rr.get("observed_evidence"))
        full_chain = text(ar.get("full_response_chain"))
        semantic_chain = text(ar.get("semantic_review_chain")) or full_chain
        verifier = semantic_verifier_profile(ar, rr, raw_text, semantic_chain)
        decision = text(verifier.get("agent_final_decision"))
        theme = verified_theme(review_theme(key, ar, rr), decision)
        observed = text(rr.get("observed_evidence")) or f"{text(ar.get('narrative_column'), 'narrative')}: {raw_text}"
        rows.append(
            {
                "respondent_key": key,
                "agent_final_decision": decision,
                "review_theme": theme,
                "supplier": text(sr.get("SUPNAME")) or text(sr.get("source")) or text(ar.get("supplier")),
                "source_workbook": workbook.name,
                "record": sr.get("record", rr.get("record")),
                "uuid": text(sr.get("uuid")) or key,
                "RID": text(sr.get("RID")),
                "ipAddress": text(sr.get("ipAddress")) or text(ar.get("ipAddress")),
                "qtime": sr.get("qtime", ar.get("qtime")),
                "computed_score": rr.get("computed_score", ""),
                "computed_action": text(rr.get("computed_action")) or "Independent audit",
                "second_pass_decision_before_agent": text(rr.get("second_pass_decision")) or "not_in_first_pass_review_queue",
                "criteria_triggered": text(rr.get("criteria_triggered")) or "independent_full_response_audit",
                "source_columns": text(rr.get("source_columns")) or text(ar.get("narrative_column")) or "full_row_audit",
                "observed_evidence": observed,
                "raw_open_end_text": raw_text,
                "response_chain_field_count": ar.get("response_chain_field_count", ""),
                "full_response_chain": full_chain,
                "semantic_review_chain_field_count": ar.get("semantic_review_chain_field_count", ""),
                "semantic_review_chain": semantic_chain,
                "early_screening_discard_recommendation": verifier["early_screening_discard_recommendation"],
                "agent_verifier_mode": verifier["agent_verifier_mode"],
                "verifier_reason": verifier["verifier_reason"],
                "verifier_counterevidence": verifier["verifier_counterevidence"],
                "semantic_discard_basis": verifier["semantic_discard_basis"],
                "semantic_pattern_findings": verifier["semantic_pattern_findings"],
                "agent_semantic_judgment": semantic_judgment(key, decision, theme, raw_text, semantic_chain, ar, verifier),
                "agent_linguistic_fluency_assessment": language_assessment(decision, raw_text),
                "agent_trust_rationale": f"The recommendation is based on the focused semantic chain, the full response chain, timing, source context, and the final review result. Theme: {theme}.",
                "agent_recommended_next_step": next_step(decision, theme),
                "agent_discard_rationale": "The row has converging evidence for exclusion review." if decision == "discard" else "",
                "independent_narrative_quality": text(ar.get("narrative_quality")),
                "independent_risk_factors": text(ar.get("independent_risk_factors")),
                "independent_suggested_action": text(ar.get("independent_suggested_action")),
            }
        )

    judgments = pd.DataFrame(rows)
    judgments.to_csv(run_dir / "agent_review_judgment_table.csv", index=False)

    discard = judgments[judgments["agent_final_decision"].eq("discard")].copy()
    discard.to_csv(run_dir / "agent_discard_set.csv", index=False)

    kept = judgments[judgments["agent_final_decision"].ne("discard")].copy()
    synthesis = pd.DataFrame(
        [synthesis_for_theme(theme, group) for theme, group in kept.groupby("review_theme", sort=False)]
    ).sort_values("kept_review_rows", ascending=False)
    synthesis.to_csv(run_dir / "agent_kept_review_synthesis_table.csv", index=False)

    lines = ["# Kept review synthesis", "", f"Kept reviewed rows: {len(kept)}.", ""]
    for _, row in synthesis.iterrows():
        lines.extend(
            [
                f"## {row['theme']}",
                f"Rows: {int(row['kept_review_rows'])}",
                "",
                f"Why kept: {row['why_kept']}",
                "",
                f"Next-pass recommendation: {row['survey_question_or_parameter_recommendation']}",
                "",
                f"Suggested quality parameter: {row['suggested_quality_parameter']}",
                "",
                f"Examples: {row['example_respondent_keys']}",
                "",
            ]
        )
    (run_dir / "agent_kept_review_synthesis.md").write_text("\n".join(lines), encoding="utf-8")

    summary = [
        "# Final review judgment summary",
        "",
        f"Total source rows: {len(source)}.",
        f"Rows in first-pass review queue: {len(first_pass_keys)}.",
        f"Rows added by independent full-response audit: {len(audit_keys - first_pass_keys)}.",
        f"Rows reviewed in detail: {len(judgments)}.",
        f"Recommended exclusion-review rows: {len(discard)}.",
        f"Kept with review note: {len(kept)}.",
        "",
        "## Themes",
        "",
    ]
    for theme, count in judgments["review_theme"].value_counts().items():
        summary.append(f"- {theme}: {int(count)}")
    (run_dir / "agent_review_judgment_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    verified = [
        "# Quality review brief",
        "",
        f"Dataset: {workbook.name}",
        "",
        "## Result",
        "",
        f"- Total responses: {len(source)}.",
        f"- First-pass review rows: {len(first_pass_keys)}.",
        f"- Independent audit additions: {len(audit_keys - first_pass_keys)}.",
        f"- Rows reviewed in detail: {len(judgments)}.",
        f"- Recommended exclusion-review queue: {len(discard)}.",
        f"- Kept with review notes: {len(kept)}.",
        "",
        "## Workflow notes",
        "",
        "The workflow explored field roles and stitched each respondent's full response chain before final judgment.",
        "The final review used the criteria as a case file, then checked the full response chain before making each recommendation.",
        "We kept weak, short, speed-only, and keyword-mismatch rows unless another strong signal supported escalation.",
        "The kept rows are converted into next-pass recommendations so the next first pass has better context before scoring.",
        "",
    ]
    (run_dir / "agent_verified_quality_brief.md").write_text("\n".join(verified), encoding="utf-8")

    print(run_dir / "agent_review_judgment_table.csv")
    print(run_dir / "agent_discard_set.csv")
    print(run_dir / "agent_kept_review_synthesis_table.csv")
    print(run_dir / "agent_verified_quality_brief.md")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    build(args.run_dir.expanduser().resolve())


if __name__ == "__main__":
    main()
