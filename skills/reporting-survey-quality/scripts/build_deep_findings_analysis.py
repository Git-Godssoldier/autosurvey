#!/usr/bin/env python3
"""Build a deep findings memo from agent review and next-pass artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def text(value: object, default: str = "") -> str:
    if pd.isna(value):
        return default
    return str(value)


def pct(count: int, total: int) -> str:
    if total == 0:
        return "0.0%"
    return f"{(count / total) * 100:.1f}%"


def dataset_name(run_dir: Path, respondent: pd.DataFrame) -> str:
    if "source_workbook" in respondent and not respondent["source_workbook"].dropna().empty:
        return text(respondent["source_workbook"].dropna().iloc[0])
    return run_dir.name


def main_finding(signals: pd.DataFrame) -> str:
    if signals.empty:
        return "The run did not produce a next-pass signal inventory. Review the agent judgment table before changing the next first pass."
    top = signals.sort_values("support_rows", ascending=False).iloc[0]
    return (
        f"The largest next-pass signal was `{top['signal_id']}`, with {int(top['support_rows'])} reviewed rows. "
        f"{top['critical_signal']} The next first pass should change as follows: {top['first_pass_change']}"
    )


def what_this_run_teaches(signals: pd.DataFrame) -> list[str]:
    lessons: list[str] = []
    signal_ids = set(signals.get("signal_id", pd.Series(dtype=str)).astype(str))
    if "job_role_relevance_classifier_needed" in signal_ids:
        lessons.append(
            "The next first pass should classify job-role fields before topic scoring. Trade, construction, maintenance, repair, and tool-buying roles should not need brand words to count as relevant."
        )
    if "job_role_qualification_risk" in signal_ids or "job_role_pm_calibration_examples" in signal_ids:
        lessons.append(
            "PM rules should define the audience boundary. Role answers that are broad, managerial, real estate related, gig based, or outside the trades should become calibration examples before the scorer gets stricter."
        )
    if "brand_list_field_normalization" in signal_ids:
        lessons.append(
            "Brand-list fields need their own scoring rules. Short answers can be valid brand names or tool categories, so the next pass should normalize brands before low-effort scoring."
        )
    if "semantic_topic_relevance_replace_keyword_miss" in signal_ids:
        lessons.append(
            "Keyword topic mismatch should stay a routing signal. The agent should make the final relevance decision from the raw text and project context."
        )
    if "outro_feedback_exclusion_from_topic_scoring" in signal_ids:
        lessons.append(
            "Survey-feedback outro fields should not be scored as product-topic mismatch unless the prompt asks for a product recap."
        )
    if "duplicate_cluster_enrichment" in signal_ids:
        lessons.append(
            "Duplicate IP needs cluster context. The next pass should compare RID, source, timestamp spacing, device or browser fields, qtime, and answer similarity."
        )
    if "section_level_timing_needed" in signal_ids:
        lessons.append(
            "Speed should remain review-only unless section timing or another quality signal shows that the respondent rushed important content."
        )
    if not lessons:
        lessons.append("The next pass should use the signal inventory as calibration material before changing scoring severity.")
    return lessons


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    respondent = read_csv(run_dir / "respondent_review_table.csv")
    judgments = read_csv(run_dir / "agent_review_judgment_table.csv")
    discard = read_csv(run_dir / "agent_discard_set.csv")
    signals = read_csv(run_dir / "next_pass_signal_inventory.csv")
    sample = read_csv(run_dir / "deep_semantic_review_sample.csv")

    if judgments.empty:
        raise SystemExit(f"No agent_review_judgment_table.csv found in {run_dir}")

    total = len(respondent) if not respondent.empty else 0
    reviewed = len(judgments)
    discard_count = len(discard)
    kept_count = max(0, reviewed - discard_count)
    name = dataset_name(run_dir, respondent)

    lines = [
        "# Deep findings analysis",
        "",
        f"Dataset: {name}",
        "",
        "## Executive readout",
        "",
        f"The agent reviewed {reviewed} rows out of {total} responses. That is {pct(reviewed, total)} of the file.",
        f"The agent kept {kept_count} reviewed rows and left {discard_count} rows in the discard queue.",
        "",
        main_finding(signals),
        "",
        "## Final row decisions",
        "",
    ]
    for decision, count in judgments["agent_final_decision"].value_counts().items():
        lines.append(f"- {decision}: {int(count)}")

    lines.extend(["", "## Review themes", ""])
    for theme, count in judgments["review_theme"].value_counts().items():
        lines.append(f"- {theme}: {int(count)}")

    lines.extend(["", "## Discard recommendations", ""])
    if discard.empty:
        lines.append("No rows should be escalated after semantic review.")
    else:
        for _, row in discard.iterrows():
            lines.extend(
                [
                    f"### {row['respondent_key']}",
                    f"Evidence: {row['observed_evidence']}",
                    "",
                    f"Reason: {row['agent_discard_rationale']}",
                    "",
                    f"Next step: {row['agent_recommended_next_step']}",
                    "",
                ]
            )

    lines.extend(["## Critical signals for the next first pass", ""])
    if signals.empty:
        lines.append("No next-pass signals were available.")
    else:
        for _, row in signals.iterrows():
            lines.extend(
                [
                    f"### {row['signal_id']}",
                    f"Support: {int(row['support_rows'])} reviewed rows.",
                    "",
                    f"Signal: {row['critical_signal']}",
                    "",
                    f"Change before the next pass: {row['first_pass_change']}",
                    "",
                    f"Evidence needed: {row['evidence_needed']}",
                    "",
                    f"Escalation rule: {row['escalation_rule']}",
                    "",
                ]
            )

    lines.extend(["## What this run teaches about the survey", ""])
    for index, lesson in enumerate(what_this_run_teaches(signals), start=1):
        lines.append(f"{index}. {lesson}")
        lines.append("")

    lines.extend(["## Deep semantic sample", ""])
    if sample.empty:
        lines.append("No deep semantic sample was available.")
    else:
        for _, row in sample.head(10).iterrows():
            lines.extend(
                [
                    f"### {row['respondent_key']}",
                    f"Decision: {row['agent_final_decision']}",
                    f"Theme: {row['review_theme']}",
                    "",
                    f"Evidence: {row['observed_evidence']}",
                    "",
                    f"Semantic analysis: {row['agent_semantic_judgment']}",
                    "",
                    f"Next action: {row['agent_recommended_next_step']}",
                    "",
                ]
            )

    lines.extend(
        [
            "## Flow audit",
            "",
            "The run is complete only if the output folder contains scoring artifacts, agent review judgments, a discard set, kept review synthesis, next-pass signals, a first-pass config proposal, a deep semantic sample, a visual dashboard, and this findings memo.",
            "",
            "The next run should start by reading `next_pass_first_pass_config.json` and the workbook Datamap. The agent should map each open-end field to its field role before it applies topic mismatch or low-effort scoring.",
            "",
        ]
    )

    output = run_dir / "deep_findings_analysis.md"
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(output)


if __name__ == "__main__":
    main()
