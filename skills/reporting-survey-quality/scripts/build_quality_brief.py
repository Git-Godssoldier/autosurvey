#!/usr/bin/env python3
"""Build PM and client-facing markdown briefs from quality loop outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def pct(numerator: int, denominator: int) -> str:
    if denominator == 0:
        return "0.0%"
    return f"{(numerator / denominator) * 100:.1f}%"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True, help="Directory containing quality_summary.json and row_scores.csv.")
    parser.add_argument("--source-workbook", help="Optional workbook basename to report when row_scores.csv contains multiple workbooks.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    summary = json.loads((run_dir / "quality_summary.json").read_text(encoding="utf-8"))
    rows = pd.read_csv(run_dir / "row_scores.csv")
    source_workbook = args.source_workbook
    if not source_workbook and "source_workbook" in rows.columns and len(summary.get("source_files", [])) > 1:
        source_workbook = Path(summary["source_files"][-1]["file"]).name
    if source_workbook and "source_workbook" in rows.columns:
        filtered = rows[rows["source_workbook"] == source_workbook]
        if filtered.empty:
            raise SystemExit(f"No rows found for source workbook {source_workbook!r}")
        rows = filtered
    total = int(len(rows))
    action_counts = rows["computed_action"].value_counts().to_dict()
    severity_counts = rows["severity_level"].value_counts().to_dict() if "severity_level" in rows else {}
    owner_counts = rows["escalation_owner"].value_counts().to_dict() if "escalation_owner" in rows else {}
    disposition_counts = rows["second_pass_decision"].value_counts().to_dict() if "second_pass_decision" in rows else {}
    survivor_recommendations = (
        rows[rows["second_pass_decision"].eq("keep_with_recommendation")]["survey_question_recommendation"]
        .value_counts()
        .head(12)
        .to_dict()
        if {"second_pass_decision", "survey_question_recommendation"} <= set(rows.columns)
        else {}
    )
    survivor_examples = (
        rows[rows["second_pass_decision"].eq("keep_with_recommendation")]
        .sort_values("computed_score", ascending=False)
        .head(10)
        if "second_pass_decision" in rows
        else pd.DataFrame()
    )
    flag_counts = rows["computed_flags"].value_counts().head(15).to_dict()
    review_rows = rows[rows["computed_action"] != "Keep"].sort_values("computed_score", ascending=False).head(25)
    escalation_rows = (
        rows[rows["second_pass_decision"].eq("discard_candidate")]
        .sort_values("computed_score", ascending=False)
        .head(25)
        if "second_pass_decision" in rows
        else pd.DataFrame()
    )
    discovery_path = run_dir / "discovery_profiles.json"
    discovery = json.loads(discovery_path.read_text(encoding="utf-8")) if discovery_path.exists() else {}

    pm_lines = [
        "# Survey Quality PM Brief",
        "",
        f"Respondent score rows: {total}",
    ]
    if source_workbook:
        pm_lines.extend(["", f"Source workbook: `{source_workbook}`"])
    pm_lines.extend(
        [
            "",
            "## Review Tables",
            "- `respondent_review_table.csv`: respondent metadata, triggered criteria, explanations, tags, second-pass disposition, agent semantic analysis, linguistic fluency assessment, trust rationale, survivor rationale, discard rationale, and survey-question recommendations.",
            "- `response_criteria_evidence_table.csv`: one row per respondent criterion with observed values, disposition, agent semantic analysis, survivor/discard rationale, and scoring rationale.",
            "- `agent_annotation_table.csv`: focused Opulent annotation surface for semantic analysis, linguistic fluency assessment, trust rationale, and next steps.",
            "- `generated_criteria_catalog.csv`: all generated criteria, source columns, tags, support, and generated weight rationale.",
            "- `respondent_review_table.md`: PM-facing sample sorted by score.",
        ]
    )
    pm_lines.extend(["", "## Action Counts"])
    for action in ["Keep", "Light review", "Review closely"]:
        count = int(action_counts.get(action, 0))
        pm_lines.append(f"- {action}: {count} ({pct(count, total)})")

    if severity_counts:
        pm_lines.extend(["", "## Severity And Escalation"])
        for severity, count in severity_counts.items():
            pm_lines.append(f"- {severity}: {int(count)} ({pct(int(count), total)})")
        pm_lines.append("")
        pm_lines.append("Escalation owners:")
        for owner, count in owner_counts.items():
            pm_lines.append(f"- {owner}: {int(count)} ({pct(int(count), total)})")

    if disposition_counts:
        pm_lines.extend(["", "## Second-Pass Disposition"])
        for disposition, count in disposition_counts.items():
            pm_lines.append(f"- {disposition}: {int(count)} ({pct(int(count), total)})")
        pm_lines.append(
            "- Only `discard_candidate` rows enter the escalation queue. Rows that survive the second pass are kept with rationale and aggregated into survey-strengthening recommendations."
        )
        pm_lines.append(
            "- Annotation fields are a separate Opulent semantic-judgment layer. Scores and counts identify candidate evidence; narrative annotations explain why the judgment should be trusted."
        )

    if discovery:
        selected_profile = None
        if source_workbook and source_workbook in discovery:
            selected_profile = discovery[source_workbook]
        elif len(discovery) == 1:
            selected_profile = next(iter(discovery.values()))
        if selected_profile:
            pm_lines.extend(
                [
                    "",
                    "## Discovery Profile",
                    f"- Qtime columns: {', '.join(selected_profile.get('qtime_columns', [])) or 'none'}",
                    f"- IP columns: {', '.join(selected_profile.get('ip_columns', [])) or 'none'}",
                    f"- Matrix groups: {len(selected_profile.get('matrix_groups', {}))}",
                    f"- Open-end columns: {', '.join(selected_profile.get('open_end_columns', [])) or 'none'}",
                    f"- Brand mapping candidates: {', '.join(selected_profile.get('brand_consistency_candidate_columns', [])[:12]) or 'none'}",
                ]
            )
            analyses = selected_profile.get("candidate_analyses", [])
            if analyses:
                pm_lines.extend(["", "Candidate analyses:"])
                for analysis in analyses:
                    columns = analysis.get("candidate_columns", [])
                    column_text = ", ".join(columns[:6]) if columns else "none"
                    if len(columns) > 6:
                        column_text += f", +{len(columns) - 6} more"
                    pm_lines.append(f"- {analysis['analysis_id']}: {analysis['status']} | {column_text}")
            generated_criteria = selected_profile.get("generated_candidate_criteria", [])
            if generated_criteria:
                pm_lines.extend(["", "Generated candidate criteria:"])
                for criterion in generated_criteria[:12]:
                    pm_lines.append(
                        f"- {criterion['criterion_id']}: {criterion['status']} | tags: {', '.join(criterion.get('tags', []))}"
                    )
                if len(generated_criteria) > 12:
                    pm_lines.append(f"- +{len(generated_criteria) - 12} additional generated criteria in discovery_profiles.json")

    feedback_config = summary.get("feedback_config") or {}
    if feedback_config:
        pm_lines.extend(["", "## Feedback Trial Adjustments"])
        for finding in feedback_config.get("findings", []):
            pm_lines.append(f"- {finding['finding']}")
            pm_lines.append(f"  Trial change: {finding['trial_change']}")

    pm_lines.extend(["", "## Top Flag Patterns"])
    for flag, count in flag_counts.items():
        pm_lines.append(f"- {flag}: {int(count)} ({pct(int(count), total)})")

    pm_lines.extend(["", "## Review Queue Sample"])
    if review_rows.empty:
        pm_lines.append("- No rows currently require review.")
    else:
        for _, row in review_rows.iterrows():
            pm_lines.append(
                f"- {row['respondent_key']}: {row['computed_action']}, score {row['computed_score']}, "
                f"tags {row.get('generated_tags', '')}, {row['computed_flags']}"
            )

    if survivor_recommendations:
        pm_lines.extend(["", "## Survivor Recommendations"])
        for recommendation, count in survivor_recommendations.items():
            pm_lines.append(f"- {int(count)} survivor rows: {recommendation}")
        if not survivor_examples.empty:
            pm_lines.append("")
            pm_lines.append("Representative kept rows:")
            for _, row in survivor_examples.iterrows():
                pm_lines.append(
                    f"- {row['respondent_key']}: keep after second pass; "
                    f"{row.get('agent_semantic_analysis', row.get('survivor_rationale', ''))}; "
                    f"tags {row.get('generated_tags', '')}"
                )

    pm_lines.extend(["", "## Discard Escalation Queue"])
    if escalation_rows.empty:
        pm_lines.append("- No rows require discard escalation after second-pass analysis.")
    else:
        for _, row in escalation_rows.iterrows():
            pm_lines.append(
                f"- {row['respondent_key']}: discard candidate -> {row['escalation_owner']}; "
                f"score {row['computed_score']}; tags {row.get('generated_tags', '')}; "
                f"{row.get('agent_semantic_analysis', row.get('discard_rationale', ''))} "
                f"Trust basis: {row.get('agent_trust_rationale', '')}"
            )

    comparison = summary.get("comparison") or {}
    metrics_for_source = {}
    if source_workbook:
        metrics_for_source = summary.get("metrics", {}).get(source_workbook, {})
    elif len(summary.get("metrics", {})) == 1:
        metrics_for_source = next(iter(summary.get("metrics", {}).values()))
    agreement = metrics_for_source.get("agreement_metrics", {})
    if agreement:
        pm_lines.extend(["", "## Evaluation Metrics"])
        pm_lines.append(f"- Exact agreement: {agreement.get('exact_agreement')}")
        pm_lines.append(f"- Cohen's kappa: {agreement.get('cohen_kappa')}")
        pm_lines.append(f"- Ordinal action disagreement: {agreement.get('ordinal_action_disagreement')}")
    if comparison.get("agreement_metrics"):
        pm_lines.extend(["", "Candidate/final agreement:"])
        candidate_agreement = comparison["agreement_metrics"]
        pm_lines.append(f"- Exact agreement: {candidate_agreement.get('exact_agreement')}")
        pm_lines.append(f"- Cohen's kappa: {candidate_agreement.get('cohen_kappa')}")
        pm_lines.append(f"- Ordinal action disagreement: {candidate_agreement.get('ordinal_action_disagreement')}")

    pm_lines.extend(["", "## Rubric Status"])
    if comparison.get("available") and comparison.get("mismatch_rows") == 0:
        exact = agreement.get("exact_agreement")
        if exact == 1.0:
            pm_lines.append("- Candidate and PM final review actions match on all joined respondents; this generated scoring model is stable for this evaluation set.")
        else:
            pm_lines.append(
                "- Candidate and PM final review actions match on all joined respondents, but the generated scoring model still differs from existing actions; treat those differences as calibration findings."
            )
    elif comparison.get("available"):
        pm_lines.append(f"- Candidate/final mismatches found: {comparison.get('mismatch_rows')}. Inspect examples before changing criteria.")
    else:
        pm_lines.append("- No candidate/final comparison was available for this run.")

    client_lines = [
        "# Survey Data Quality Summary",
        "",
        "Completed responses were reviewed using a structured quality rubric covering completion time, answer consistency, straightlining, topic relevance of open-ended responses, duplicate signals, and open-end authenticity indicators.",
        "",
        "## Aggregate Results",
    ]
    for action in ["Keep", "Light review", "Review closely"]:
        count = int(action_counts.get(action, 0))
        client_lines.append(f"- {action}: {count} ({pct(count, total)})")
    client_lines.extend(
        [
        "",
        "Rows with converging quality evidence receive an additional pass before escalation. Only rows assessed as discard candidates are escalated for exclusion review; rows that survive the second pass are retained with rationale and used to improve future survey-question framing. AI-likelihood indicators are treated as review signals, not standalone proof of fraud.",
        ]
    )

    (run_dir / "pm_quality_brief.md").write_text("\n".join(pm_lines) + "\n", encoding="utf-8")
    (run_dir / "client_quality_summary.md").write_text("\n".join(client_lines) + "\n", encoding="utf-8")
    print(run_dir)


if __name__ == "__main__":
    main()
