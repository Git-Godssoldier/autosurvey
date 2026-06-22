#!/usr/bin/env python3
"""Build next-pass signals and deep semantic review samples from agent judgments."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def pct(count: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{(count / total) * 100:.1f}%"


def text(value: object, default: str = "") -> str:
    if pd.isna(value):
        return default
    return str(value)


def plain_truncate(value: object, limit: int = 700) -> str:
    raw = " ".join(text(value).split())
    if len(raw) <= limit:
        return raw
    cut = raw[:limit].rsplit(" ", 1)[0].rstrip(" .,;:")
    return cut + "..."


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def theme_rule(theme: str) -> dict[str, str]:
    lower = theme.lower()
    if "job-role keyword false positive" in lower:
        return {
            "signal_id": "job_role_relevance_classifier_needed",
            "critical_signal": "A job-role screener field was treated like a generic topic field.",
            "first_pass_change": "Classify job-role relevance before topic scoring. Trade, construction, maintenance, repair, and tool-buying roles should not need brand keywords to pass relevance.",
            "analysis_factor": "Separate audience eligibility fields from narrative topic fields.",
            "evidence_needed": "Question prompt, qcoe1 text, qIndustry, qTrade, CLASSIFY, and PM examples of qualified and unqualified roles.",
            "default_status": "scorable_after_pm_role_map",
            "escalation_rule": "Escalate only when the role is clearly outside the qualified audience and another quality signal is present, or when PM rules say the role is disqualifying.",
        }
    if "non-trade job-role mismatch" in lower or "duplicate plus non-trade qualification mismatch" in lower:
        return {
            "signal_id": "job_role_qualification_risk",
            "critical_signal": "Some respondents described roles outside the target contractor or trade audience.",
            "first_pass_change": "Add a job-role qualification risk analysis that compares qcoe1 against screener fields before scoring.",
            "analysis_factor": "Track non-trade, gig-only, service, software, retail, HR, IT, and generic management roles separately from respondent-quality failures.",
            "evidence_needed": "qcoe1 text, qIndustry, qTrade, CLASSIFY, qc flags, PM qualification rules, and respondent source.",
            "default_status": "review_only_until_pm_rules",
            "escalation_rule": "Escalate when a non-trade role is paired with duplicate evidence, direct non-cooperation, or PM-confirmed disqualification.",
        }
    if "ambiguous job-role" in lower:
        return {
            "signal_id": "job_role_pm_calibration_examples",
            "critical_signal": "Manager, owner, property, operations, and real estate role text needs PM interpretation.",
            "first_pass_change": "Collect PM-labeled role examples and use them in the next project context before scoring qcoe1 harder.",
            "analysis_factor": "Create qualified, maybe-qualified, and unqualified role groups.",
            "evidence_needed": "Representative qcoe1 examples, PM labels, qIndustry, qTrade, and survey qualification rules.",
            "default_status": "needs_feedback",
            "escalation_rule": "Keep ambiguous job-role answers until PM labels define the boundary.",
        }
    if "brand or tool category answer" in lower or "brand answer plausible" in lower or "thin brand" in lower:
        return {
            "signal_id": "brand_list_field_normalization",
            "critical_signal": "Short brand and tool-category answers were mistaken for low-effort open ends.",
            "first_pass_change": "Classify unaided brand-list fields before low-effort scoring. Normalize valid short brand names and tool categories.",
            "analysis_factor": "Use a brand dictionary and tool-category dictionary for qcoe2 and related brand-list fields.",
            "evidence_needed": "Field prompt, qcoe2 values, known brand list, spelling variants, and PM-approved category terms.",
            "default_status": "scorable_after_brand_dictionary",
            "escalation_rule": "Escalate only when brand-list answers are nonsense, hostile, repeated gibberish, or paired with another strong quality signal.",
        }
    if "direct non-cooperation" in lower or "abusive" in lower:
        return {
            "signal_id": "direct_non_cooperation_open_end",
            "critical_signal": "A respondent gave hostile or directly non-cooperative open-end content.",
            "first_pass_change": "Add direct refusal, profanity, and hostile-content detection as a high-priority review signal.",
            "analysis_factor": "Separate hostile refusal from ordinary short brand answers.",
            "evidence_needed": "Raw open-end text, source field, nearby brand answers, and PM removal policy.",
            "default_status": "review_for_discard",
            "escalation_rule": "Escalate direct refusal or hostile content when it appears in a required open-end field.",
        }
    if "keyword false positive" in lower:
        return {
            "signal_id": "semantic_topic_relevance_replace_keyword_miss",
            "critical_signal": "Keyword topic mismatch created many false positives.",
            "first_pass_change": "Do not score keyword mismatch as a final topic signal. Use it only to route rows to semantic relevance review.",
            "analysis_factor": "Add project vocabulary classes before scoring. Include category terms, adjacent tasks, and common respondent wording.",
            "evidence_needed": "Raw open-end text, source question, project topic map, and PM examples of acceptable wording.",
            "default_status": "review_only_until_validated",
            "escalation_rule": "Escalate only when semantic review confirms non-response and another strong quality signal is present.",
        }
    if "outro survey feedback" in lower:
        return {
            "signal_id": "outro_feedback_exclusion_from_topic_scoring",
            "critical_signal": "Outro survey feedback was treated as product-topic evidence.",
            "first_pass_change": "Classify outro fields before scoring. Survey feedback should not be product topic mismatch evidence.",
            "analysis_factor": "Split open ends into product answers, qualification answers, other-specify answers, and survey-feedback answers.",
            "evidence_needed": "Question label, field name, prompt text when available, and sample values.",
            "default_status": "do_not_score_for_product_topic",
            "escalation_rule": "Do not escalate from outro feedback unless the project requires a substantive product recap.",
        }
    if "product-adjacent" in lower:
        return {
            "signal_id": "product_adjacent_vocabulary_expansion",
            "critical_signal": "Relevant product-adjacent wording missed the seed keywords.",
            "first_pass_change": "Add semantic synonyms and related use cases to the project topic map before topic scoring.",
            "analysis_factor": "Capture adjacent category terms and benefits that respondents naturally use.",
            "evidence_needed": "Accepted open-end examples and project category terms.",
            "default_status": "scorable_after_topic_map_update",
            "escalation_rule": "Keep product-adjacent wording unless the full answer is evasive or incoherent.",
        }
    if "duplicate" in lower:
        return {
            "signal_id": "duplicate_cluster_enrichment",
            "critical_signal": "Shared IP signals need more context before discard.",
            "first_pass_change": "Pair duplicate IP with RID, source, timestamp spacing, device or browser fields, and answer similarity.",
            "analysis_factor": "Add cluster-level duplicate review instead of row-only duplicate flags.",
            "evidence_needed": "IP address, RID, source, timestamp, device or browser, qtime, and answer similarity.",
            "default_status": "review_only_unless_correlated",
            "escalation_rule": "Escalate duplicate rows only when another strong signal or high answer similarity appears.",
        }
    if "speed" in lower:
        return {
            "signal_id": "section_level_timing_needed",
            "critical_signal": "Speed-only rows created review volume without enough discard evidence.",
            "first_pass_change": "Keep total qtime as a routing signal and add page or section timing when available.",
            "analysis_factor": "Separate rushed survey sections from short but plausible completes.",
            "evidence_needed": "Total qtime, page timings, section timings, and high-value question exposure time.",
            "default_status": "review_only",
            "escalation_rule": "Escalate speed only when it is paired with inattentive answers, low effort text, or straightlining.",
        }
    if "low-effort" in lower:
        return {
            "signal_id": "open_end_question_criticality_map",
            "critical_signal": "Thin open-end answers need question context before scoring.",
            "first_pass_change": "Map which open ends are critical before assigning low-effort points.",
            "analysis_factor": "Separate optional low-value text fields from qualification-critical text fields.",
            "evidence_needed": "Prompt text, answer requirement, PM examples, and field role in the survey.",
            "default_status": "needs_question_mapping",
            "escalation_rule": "Escalate low-effort text only when the field is critical or another strong quality signal is present.",
        }
    if "ambiguous" in lower or "weak project-fit" in lower:
        return {
            "signal_id": "pm_semantic_calibration_examples",
            "critical_signal": "Ambiguous semantic cases need PM examples before the next pass can score them harder.",
            "first_pass_change": "Collect accepted and rejected examples, then add them to the project context before scoring.",
            "analysis_factor": "Use PM labels to define the boundary between awkward wording and non-response.",
            "evidence_needed": "Representative kept rows, PM decisions, prompt text, and project context.",
            "default_status": "needs_feedback",
            "escalation_rule": "Keep ambiguous rows until PM examples define the rule.",
        }
    return {
        "signal_id": "general_review_only_signal",
        "critical_signal": "Reviewed rows did not create a specific new discard rule.",
        "first_pass_change": "Keep this signal as review-only until PM adjudication provides clearer evidence.",
        "analysis_factor": "Track the pattern across runs.",
        "evidence_needed": "Agent review rows and PM labels.",
        "default_status": "needs_feedback",
        "escalation_rule": "Do not escalate without converging evidence.",
    }


def build_signal_inventory(judgments: pd.DataFrame, synthesis: pd.DataFrame) -> pd.DataFrame:
    if synthesis.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    total_reviewed = max(1, len(judgments))
    for _, item in synthesis.iterrows():
        theme = text(item.get("theme"))
        rule = theme_rule(theme)
        support = int(item.get("kept_review_rows", 0))
        rows.append(
            {
                "theme": theme,
                "support_rows": support,
                "support_rate_among_reviewed": pct(support, total_reviewed),
                "example_respondent_keys": text(item.get("example_respondent_keys")),
                **rule,
                "why_kept": text(item.get("why_kept")),
                "survey_question_or_parameter_recommendation": text(item.get("survey_question_or_parameter_recommendation")),
                "suggested_quality_parameter": text(item.get("suggested_quality_parameter")),
                "issue_pattern": text(item.get("issue_pattern")),
            }
        )
    raw = pd.DataFrame(rows)
    grouped_rows: list[dict[str, object]] = []
    for signal_id, group in raw.groupby("signal_id", sort=False):
        first = group.iloc[0].to_dict()
        support = int(group["support_rows"].sum())
        first["theme"] = " | ".join(group["theme"].astype(str))
        first["support_rows"] = support
        first["support_rate_among_reviewed"] = pct(support, max(1, len(judgments)))
        first["example_respondent_keys"] = " | ".join(group["example_respondent_keys"].astype(str))
        first["why_kept"] = " | ".join(group["why_kept"].astype(str).drop_duplicates())
        first["survey_question_or_parameter_recommendation"] = " | ".join(
            group["survey_question_or_parameter_recommendation"].astype(str).drop_duplicates()
        )
        first["suggested_quality_parameter"] = " | ".join(group["suggested_quality_parameter"].astype(str).drop_duplicates())
        first["issue_pattern"] = " | ".join(group["issue_pattern"].astype(str).drop_duplicates())
        grouped_rows.append(first)
    return pd.DataFrame(grouped_rows).sort_values(["support_rows", "signal_id"], ascending=[False, True])


def next_pass_config(inventory: pd.DataFrame) -> dict[str, object]:
    rules = []
    for _, row in inventory.iterrows():
        rules.append(
            {
                "signal_id": row["signal_id"],
                "theme": row["theme"],
                "support_rows": int(row["support_rows"]),
                "default_status": row["default_status"],
                "first_pass_change": row["first_pass_change"],
                "evidence_needed": row["evidence_needed"],
                "escalation_rule": row["escalation_rule"],
            }
        )
    return {
        "purpose": "Use these proposed rules before the next first-pass scoring run.",
        "rules": rules,
        "guardrails": [
            "Treat keyword topic mismatch as candidate evidence until semantic review confirms it.",
            "Do not score survey-feedback outro fields as product topic mismatch.",
            "Do not escalate speed-only or duplicate-only rows without another strong quality signal.",
            "Require question-level context before low-effort open ends become discard evidence.",
        ],
    }


def sample_rows(judgments: pd.DataFrame, sample_size: int) -> pd.DataFrame:
    if judgments.empty:
        return pd.DataFrame()
    selected: list[pd.DataFrame] = []
    discards = judgments[judgments["agent_final_decision"].astype(str).eq("discard")]
    if not discards.empty:
        selected.append(discards)
    remaining_slots = max(0, sample_size - sum(len(frame) for frame in selected))
    if remaining_slots:
        groups = judgments[judgments["agent_final_decision"].astype(str).ne("discard")].groupby("review_theme", dropna=False)
        reps = []
        for _, group in groups:
            sorted_group = group.sort_values("computed_score", ascending=False)
            reps.append(sorted_group.head(1))
        if reps:
            selected.append(pd.concat(reps, ignore_index=True).head(remaining_slots))
    sample = pd.concat(selected, ignore_index=True) if selected else judgments.head(sample_size).copy()
    sample = sample.drop_duplicates(subset=["respondent_key"]).head(sample_size)
    return sample


def learning_for_theme(theme: str) -> str:
    rule = theme_rule(theme)
    return f"{rule['first_pass_change']} {rule['escalation_rule']}"


def write_markdown(
    run_dir: Path,
    judgments: pd.DataFrame,
    inventory: pd.DataFrame,
    sample: pd.DataFrame,
) -> None:
    total_reviewed = len(judgments)
    discard_count = int(judgments["agent_final_decision"].astype(str).eq("discard").sum()) if not judgments.empty else 0
    kept_count = max(0, total_reviewed - discard_count)

    signal_lines = [
        "# Next-pass signal inventory",
        "",
        f"Agent reviewed rows: {total_reviewed}",
        f"Agent discard rows: {discard_count}",
        f"Kept review rows: {kept_count}",
        "",
        "## Signals to feed into the next first pass",
    ]
    if inventory.empty:
        signal_lines.append("No next-pass signals were generated.")
    else:
        for _, row in inventory.iterrows():
            signal_lines.extend(
                [
                    f"## {row['signal_id']}",
                    f"Theme: {row['theme']}",
                    f"Support: {int(row['support_rows'])} reviewed rows.",
                    "",
                    f"Critical signal: {row['critical_signal']}",
                    "",
                    f"First-pass change: {row['first_pass_change']}",
                    "",
                    f"Evidence needed: {row['evidence_needed']}",
                    "",
                    f"Escalation rule: {row['escalation_rule']}",
                    "",
                    f"Next survey improvement: {row['survey_question_or_parameter_recommendation']}",
                    "",
                ]
            )
    (run_dir / "next_pass_signal_inventory.md").write_text("\n".join(signal_lines) + "\n", encoding="utf-8")

    sample_lines = [
        "# Deep semantic review sample",
        "",
        "This sample shows how the agent moved from a script flag to a final decision.",
        "Use these rows to improve the next first pass and to create PM calibration examples.",
        "",
    ]
    if sample.empty:
        sample_lines.append("No review rows were available for deep semantic analysis.")
    else:
        for _, row in sample.iterrows():
            theme = text(row.get("review_theme"))
            sample_lines.extend(
                [
                    f"## {row['respondent_key']}",
                    f"Final agent decision: {row['agent_final_decision']}",
                    f"Theme: {theme}",
                    f"Score: {row.get('computed_score', '')}",
                    f"Supplier: {row.get('supplier', '')}",
                    f"Qtime: {row.get('qtime', '')}",
                    "",
                    f"Observed evidence: {plain_truncate(row.get('observed_evidence'), 900)}",
                    "",
                    f"Raw text reviewed: {plain_truncate(row.get('raw_open_end_text'), 900)}",
                    "",
                    f"Semantic analysis: {plain_truncate(row.get('agent_semantic_judgment'), 1100)}",
                    "",
                    f"Language assessment: {plain_truncate(row.get('agent_linguistic_fluency_assessment'), 800)}",
                    "",
                    f"Trust basis: {plain_truncate(row.get('agent_trust_rationale'), 900)}",
                    "",
                    f"Next action: {plain_truncate(row.get('agent_recommended_next_step'), 800)}",
                    "",
                    f"Learning for next pass: {learning_for_theme(theme)}",
                    "",
                ]
            )
    (run_dir / "deep_semantic_review_sample.md").write_text("\n".join(sample_lines) + "\n", encoding="utf-8")

    log_lines = [
        "# Workflow improvement log",
        "",
        "## Required follow-up after each scoring run",
        "1. Build `agent_review_judgment_table.csv` for every row with a review signal.",
        "2. Build `agent_discard_set.csv` from the final agent decisions only.",
        "3. Build `agent_kept_review_synthesis_table.csv` from rows kept with review notes.",
        "4. Build `next_pass_signal_inventory.csv` before the next scoring run.",
        "5. Build `deep_semantic_review_sample.md` and return a subset of the sample in the work summary.",
        "",
        "## Run-specific learning",
    ]
    if inventory.empty:
        log_lines.append("No run-specific learning was available.")
    else:
        for _, row in inventory.iterrows():
            log_lines.append(f"- {row['signal_id']}: {row['first_pass_change']}")
    (run_dir / "workflow_improvement_log.md").write_text("\n".join(log_lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--sample-size", type=int, default=12)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    judgments = read_csv(run_dir / "agent_review_judgment_table.csv")
    synthesis = read_csv(run_dir / "agent_kept_review_synthesis_table.csv")

    if judgments.empty:
        raise SystemExit(f"No agent_review_judgment_table.csv found in {run_dir}")

    inventory = build_signal_inventory(judgments, synthesis)
    inventory.to_csv(run_dir / "next_pass_signal_inventory.csv", index=False)
    config = next_pass_config(inventory)
    (run_dir / "next_pass_first_pass_config.json").write_text(json.dumps(config, indent=2, ensure_ascii=True), encoding="utf-8")

    sample = sample_rows(judgments, args.sample_size)
    sample.to_csv(run_dir / "deep_semantic_review_sample.csv", index=False)
    write_markdown(run_dir, judgments, inventory, sample)

    print(run_dir / "next_pass_signal_inventory.csv")
    print(run_dir / "next_pass_first_pass_config.json")
    print(run_dir / "deep_semantic_review_sample.md")
    print(run_dir / "workflow_improvement_log.md")


if __name__ == "__main__":
    main()
