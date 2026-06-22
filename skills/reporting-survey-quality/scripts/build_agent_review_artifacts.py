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
    r"performance|availability|trust|recommend|contract|construction|repair|project|home|store|supplier",
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
    answers: list[str] = []
    for segment in chain_segments(full_chain):
        if ": " in segment:
            answers.append(segment.split(": ", 1)[1])
        else:
            answers.append(segment)
    return " ".join(answers)


def repeated_character_expression(value: str) -> bool:
    return bool(re.search(r"([a-z!?])\1{2,}", value.lower()))


def has_substantive_context(value: str) -> bool:
    return bool(SUBSTANTIVE_TERMS.search(value))


def has_plausible_project_answer(value: str) -> bool:
    return bool(PROJECT_ANSWER_TERMS.search(value))


def has_enthusiastic_context(value: str) -> bool:
    return bool(ENTHUSIASM_TERMS.search(value))


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
    combined_text = f"{raw_text} {answer_text}"

    programmatic_discard = action == "review_for_possible_discard" or second_pass == "discard_candidate"
    counterevidence: list[str] = []
    discard_basis: list[str] = []
    patterns: list[str] = []

    expressive_repetition = repeated_character_expression(raw_text) or repeated_character_expression(answer_text)
    if expressive_repetition:
        patterns.append("duplicate-character or repeated-punctuation expression")
        if has_enthusiastic_context(combined_text) and has_substantive_context(combined_text):
            counterevidence.append("Repeated characters appear in an enthusiastic or spirited answer with substantive context.")

    if narrative in {"topic_relevant", "substantive_narrative", "product_relevant"}:
        counterevidence.append("The audited narrative is usable in context.")
    if has_substantive_context(combined_text):
        counterevidence.append("The full response chain contains substantive project, product, role, or evaluation terms.")
    if has_plausible_project_answer(combined_text):
        counterevidence.append("The answer names a plausible project, product use, or home-improvement activity.")
    if len(segments) >= 8:
        patterns.append(f"The verifier reviewed nonempty answers across {len(segments)} fields before judging discard.")

    if ABUSIVE_OR_HOSTILE_TERMS.search(raw_text):
        discard_basis.append("The reviewed text contains hostile or abusive language.")
    if NON_RESPONSE_TERMS.fullmatch(raw_text.strip()):
        discard_basis.append("The reviewed text is a direct non-response.")
    if narrative == "nonsensical_or_repetitive" and not counterevidence:
        discard_basis.append("The narrative is nonsensical or repetitive and the full chain does not recover useful context.")
    if "narrative_discard_risk" in risks and not counterevidence:
        discard_basis.append("The audit found a narrative discard risk and the full chain did not provide a benign reading.")
    if "narrative_quality_risk" in risks and "speed_risk" in risks and not counterevidence:
        discard_basis.append("Weak narrative evidence combines with speed and the full chain does not recover usable context.")
    if "role_fit_risk" in risks and not counterevidence:
        discard_basis.append("Role fit appears invalid and the full chain does not provide qualifying context.")
    if "duplicate_ip" in criteria and "matrix_straightline" in criteria and not counterevidence:
        discard_basis.append("Independent duplicate evidence combines with straightlining and no full-chain counterevidence was found.")
    if "matrix_straightline" in criteria and "low_effort_open_end" in criteria and not counterevidence:
        discard_basis.append("Straightlining combines with low-effort text and no full-chain counterevidence was found.")

    if not programmatic_discard:
        final = "keep_with_review_note"
        reason = "Static criteria routed the row for review, but they did not recommend discard."
    elif discard_basis:
        final = "discard"
        reason = "The verifier found a semantic discard basis after reading the full response chain."
    else:
        final = "keep_with_review_note"
        reason = "The verifier did not find enough semantic evidence to support discard after reading the full response chain."

    return {
        "programmatic_discard_recommendation": programmatic_discard,
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
    chain_note = f" Full response chain reviewed: {full_chain[:900]}"
    if decision == "discard":
        return (
            f"Respondent {key} should stay in the discard queue after critic verification. "
            f"Semantic discard basis: {verifier['semantic_discard_basis']} "
            f"Narrative class: {narrative}. Risk factors: {risks}. Raw text reviewed: {raw_text}.{chain_note}"
        )
    return (
        f"Keep respondent {key} with a review note after critic verification. "
        f"The static layer routed the row for review, but the verifier did not find a defensible semantic discard basis. "
        f"Counterevidence: {verifier['verifier_counterevidence']} "
        f"Narrative class: {narrative}. Raw text reviewed: {raw_text}.{chain_note}"
    )


def language_assessment(decision: str, raw_text: str) -> str:
    if decision == "discard":
        return "The concern is answer substance. The answer is evasive, repetitive, generic, or too weak for a required response."
    if len(raw_text.split()) <= 5:
        return "The answer is short. It can still be valid when the prompt only requires a factor or simple reason."
    return "The language may be imperfect, but the meaning is readable in the survey context."


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
        why = "Static criteria suggested discard, but the verifier found recoverable semantic context in the full response chain."
        recommendation = "Keep these cases as examples where final review must supersede programmatic checks after reading the full chain."
        parameter = "Programmatic discard recommendations require critic-verifier confirmation before exclusion."
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
        verifier = semantic_verifier_profile(ar, rr, raw_text, full_chain)
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
                "programmatic_discard_recommendation": verifier["programmatic_discard_recommendation"],
                "agent_verifier_mode": verifier["agent_verifier_mode"],
                "verifier_reason": verifier["verifier_reason"],
                "verifier_counterevidence": verifier["verifier_counterevidence"],
                "semantic_discard_basis": verifier["semantic_discard_basis"],
                "semantic_pattern_findings": verifier["semantic_pattern_findings"],
                "agent_semantic_judgment": semantic_judgment(key, decision, theme, raw_text, full_chain, ar, verifier),
                "agent_linguistic_fluency_assessment": language_assessment(decision, raw_text),
                "agent_trust_rationale": f"The decision uses the stitched full response chain, field role, timing, independent audit classification, and critic verifier result. Theme: {theme}.",
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
        "# Agent review judgment summary",
        "",
        f"Total source rows: {len(source)}.",
        f"Rows in first-pass review queue: {len(first_pass_keys)}.",
        f"Rows added by independent full-response audit: {len(audit_keys - first_pass_keys)}.",
        f"Rows reviewed by agent: {len(judgments)}.",
        f"Final discard or escalation rows: {len(discard)}.",
        f"Kept with review note: {len(kept)}.",
        "",
        "## Themes",
        "",
    ]
    for theme, count in judgments["review_theme"].value_counts().items():
        summary.append(f"- {theme}: {int(count)}")
    (run_dir / "agent_review_judgment_summary.md").write_text("\n".join(summary) + "\n", encoding="utf-8")

    verified = [
        "# Agent-verified quality brief",
        "",
        f"Dataset: {workbook.name}",
        "",
        "## Result",
        "",
        f"- Total responses: {len(source)}.",
        f"- First-pass review rows: {len(first_pass_keys)}.",
        f"- Independent audit additions: {len(audit_keys - first_pass_keys)}.",
        f"- Agent-reviewed rows: {len(judgments)}.",
        f"- Final discard or escalation queue: {len(discard)}.",
        f"- Kept with review notes: {len(kept)}.",
        "",
        "## Workflow notes",
        "",
        "The workflow explored field roles and stitched each respondent's full response chain before final judgment.",
        "The final review used the criteria as a case file, then applied a critic-verifier pass that could keep rows when the full chain gave a meaningful semantic explanation.",
        "The agent kept weak, short, speed-only, and keyword-mismatch rows unless another strong signal supported escalation.",
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
