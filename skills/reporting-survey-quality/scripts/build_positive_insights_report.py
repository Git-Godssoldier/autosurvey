#!/usr/bin/env python3
"""Build a positive findings report from final survey-quality run artifacts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.exists() else ""


def text(value: object) -> str:
    if pd.isna(value):
        return ""
    raw = " ".join(str(value).split())
    replacements = {
        "programmatic checks": "early screening checks",
        "Programmatic checks": "Early screening checks",
        "programmatic layer": "early screening layer",
        "Programmatic layer": "Early screening layer",
        "programmatic discard recommendations": "early screening discard recommendations",
        "Programmatic discard recommendations": "Early screening discard recommendations",
        "programmatic": "early screening",
        "Programmatic": "Early screening",
        "preferred store": "mapped preference field",
        "Preferred store": "Mapped preference field",
        "reason for preference": "mapped reason field",
        "Reason for preference": "Mapped reason field",
        "purchase behavior": "mapped behavior field",
        "Purchase behavior": "Mapped behavior field",
        "survey recap": "mapped closing open-end",
        "Survey recap": "Mapped closing open-end",
        "no enough evidence": "not enough evidence",
    }
    for old, new in replacements.items():
        raw = raw.replace(old, new)
    return raw


def truncate(value: object, limit: int = 360) -> str:
    raw = text(value)
    if len(raw) <= limit:
        return raw
    cut = raw[:limit].rsplit(" ", 1)[0].rstrip(" .,;:")
    return cut + "..."


def pct(value: int, total: int) -> str:
    return "0.0%" if total == 0 else f"{(value / total) * 100:.1f}%"


def citation(path: Path) -> str:
    return f"`{path.name}`"


def readable_label(value: object) -> str:
    raw = text(value)
    if not raw:
        return "not classified"
    label = raw.replace("_", " ").replace("-", " ")
    return " ".join(label.split())


def response_key(row: pd.Series) -> str:
    for column in ("respondent_key", "uuid", "record", "RID"):
        if column in row and text(row[column]):
            return text(row[column])
    return "unknown respondent"


def chain_excerpt(chain: object, limit: int = 520) -> str:
    raw = text(chain)
    if not raw:
        return "No response chain text was available."
    parts = [part.strip() for part in raw.split("||") if part.strip()]

    def segment_answer(part: str) -> str:
        if "]: " in part:
            return part.split("]: ", 1)[1].strip()
        if ": " in part:
            return part.rsplit(": ", 1)[1].strip()
        return part.strip()

    def score_part(part: str) -> int:
        lower = part.lower()
        answer = segment_answer(part)
        letters = sum(ch.isalpha() for ch in answer)
        if letters < 6:
            return -100
        if answer.replace(".", "", 1).isdigit():
            return -100
        score = min(len(answer), 120)
        for token in ("narrative", "open", "other", "why", "reason", "outro", "specify", "explain", "preferred", "experience"):
            if token in lower:
                score += 50
        for token in ("termflags", "region", "record", "uuid", "ipaddress", "qtime", "demographic_field"):
            if token in lower:
                score -= 60
        return score

    ranked = sorted(parts, key=score_part, reverse=True)
    useful: list[str] = []
    for part in ranked:
        if score_part(part) > 0:
            useful.append(part)
        if len(useful) >= 3:
            break
    for part in parts:
        if len(useful) >= 3:
            break
        if part not in useful and score_part(part) > -100:
            useful.append(part)
    if not useful:
        useful = parts[:3]
    return truncate(" | ".join(useful), limit)


def source_total(summary: dict, respondent: pd.DataFrame, audit: pd.DataFrame) -> int:
    for key in ("total_rows", "source_rows", "respondent_rows", "rows"):
        value = summary.get(key)
        if isinstance(value, int):
            return value
    for frame in (audit, respondent):
        if not frame.empty:
            return len(frame)
    return 0


def strong_examples(best_worst: pd.DataFrame, audit: pd.DataFrame, limit: int = 5) -> pd.DataFrame:
    if not best_worst.empty and "group" in best_worst:
        best = best_worst[best_worst["group"].astype(str).str.lower().eq("best")].copy()
        if not best.empty:
            return best.head(limit)
    if audit.empty:
        return pd.DataFrame()
    if "independent_suggested_action" in audit:
        good = audit[
            audit["independent_suggested_action"]
            .astype(str)
            .str.contains("keep_no_issue|review_or_pm_calibration", case=False, na=False)
        ].copy()
    else:
        good = audit.copy()
    if "response_chain_field_count" in good:
        good = good.sort_values("response_chain_field_count", ascending=False)
    return good.head(limit)


def top_themes(df: pd.DataFrame, column: str, limit: int = 8) -> list[tuple[str, int]]:
    if df.empty or column not in df:
        return []
    counts = df[column].fillna("missing").astype(str).value_counts().head(limit)
    return [(str(index), int(value)) for index, value in counts.items()]


def demographic_lines(demo: pd.DataFrame, limit: int = 8) -> list[str]:
    if demo.empty:
        return ["No demographic summary was available for this run."]
    preferred = ["qGender", "qager1", "age", "qEd", "qStateVer", "qEmploy", "qUSHHI", "q44", "q45", "qPolitics"]
    scored = demo.copy()
    if "field" in scored:
        scored["_rank"] = scored["field"].astype(str).apply(lambda value: preferred.index(value) if value in preferred else len(preferred))
        scored = scored.sort_values(["_rank", "field"])
    lines: list[str] = []
    for _, row in scored.head(limit).iterrows():
        field = text(row.get("field")) or "field"
        top_values = truncate(row.get("top_values"), 220)
        nonempty = text(row.get("nonempty_rows"))
        question = truncate(row.get("question_text"), 160)
        if top_values:
            lines.append(
                f"- `{field}` had {nonempty or 'available'} nonempty responses. Top values: {top_values}. "
                f"Question text: {question or 'not available'}"
            )
    return lines or ["No demographic fields had enough readable values to summarize."]


def packet_contains_all(packet: Path, discards: pd.DataFrame) -> list[str]:
    if not packet.exists() or discards.empty or "respondent_key" not in discards:
        return []
    packet_text = read_text(packet).lower()
    missing: list[str] = []
    for key in discards["respondent_key"].dropna().astype(str):
        if key and key.lower() not in packet_text:
            missing.append(key)
    return missing


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir

    summary = read_json(run_dir / "quality_summary.json")
    respondent = read_csv(run_dir / "respondent_review_table.csv")
    judgments = read_csv(run_dir / "agent_review_judgment_table.csv")
    discards = read_csv(run_dir / "agent_discard_set.csv")
    kept = read_csv(run_dir / "agent_kept_review_synthesis_table.csv")
    best_worst = read_csv(run_dir / "full_chain_best_worst_examples.csv")
    audit = read_csv(run_dir / "independent_full_response_audit.csv")
    demo = read_csv(run_dir / "demographic_summary.csv")

    total = source_total(summary, respondent, audit)
    reviewed = len(judgments)
    discard_count = len(discards)
    kept_review = max(reviewed - discard_count, 0)
    audit_reconciles = bool(total and len(audit) == total)
    missing_packet_rows = packet_contains_all(run_dir / "agent_escalation_packet.md", discards)

    lines: list[str] = [
        "# Positive findings and response-quality report",
        "",
        "> Draft evidence note. A script assembled the counts, citations, and example rows below. The agent must read the evidence and rewrite the final client-facing analysis before delivery.",
        "",
        "## Read this first",
        (
            f"We reviewed {total or 'the available'} source responses. {reviewed} rows received final semantic review, "
            f"and {discard_count} {'row is' if discard_count == 1 else 'rows are'} recommended for exclusion review. "
            "The useful finding is not only the discard set. "
            "The retained data contains strong response chains that show what credible participation looks like in this study, "
            "and those strong rows should shape the next pass of scoring. "
            f"Sources: {citation(run_dir / 'quality_summary.json')}, {citation(run_dir / 'agent_review_judgment_table.csv')}, "
            f"and {citation(run_dir / 'independent_full_response_audit.csv')}."
        ),
        "",
        "## What good data looks like in this run",
    ]

    examples = strong_examples(best_worst, audit)
    if examples.empty:
        lines.append("The run did not contain a best-response example table. Add one before client delivery.")
    else:
        for _, row in examples.iterrows():
            key = response_key(row)
            decision = text(row.get("agent_final_decision")) or text(row.get("independent_suggested_action")) or "kept"
            readable_decision = readable_label(decision)
            basis = truncate(row.get("rank_basis") or row.get("verifier_counterevidence") or row.get("independent_risk_factors"), 260)
            excerpt = chain_excerpt(row.get("full_response_chain"))
            lines.extend(
                [
                    f"### {key}",
                    (
                        f"This row is a useful calibration example because the review found a defensible reason to keep it: {readable_decision}. "
                        f"{basis or 'The chain contains enough context to support retention.'} "
                        f"Representative chain read: \"{excerpt}\" Source: {citation(run_dir / 'full_chain_best_worst_examples.csv')}."
                    ),
                    "",
                ]
            )

    lines.extend(["## Positive research signals", ""])
    for theme, count in top_themes(audit, "narrative_quality", 6):
        lines.append(
            f"- {readable_label(theme).capitalize()} appeared in {count} full-chain audit rows. This helps separate usable concise answers from true non-response. "
            f"Source: {citation(run_dir / 'independent_full_response_audit.csv')}."
        )
    if not kept.empty:
        lines.append("")
        lines.append("The retained review rows also produced survey-improvement signals:")
        for _, row in kept.head(6).iterrows():
            theme = text(row.get("theme"))
            count = text(row.get("kept_review_rows"))
            why = truncate(row.get("why_kept"), 260)
            recommendation = truncate(row.get("survey_question_or_parameter_recommendation"), 260)
            lines.append(f"- {readable_label(theme).capitalize()} covered {count or 'some'} retained rows. {why} Recommended next step: {recommendation}")

    lines.extend(["", "## Demographic and aggregate context", ""])
    lines.extend(demographic_lines(demo))

    lines.extend(["", "## Why retained review rows stayed in the data", ""])
    if reviewed == 0:
        lines.append("No final semantic review rows were available, so this report cannot assess retained review rows.")
    else:
        lines.append(
            f"{kept_review} reviewed rows were retained after full-chain review. Valid short answers, misspellings, shared technical context, "
            "or energetic wording can look weak to an early screen while still carrying real respondent meaning. "
            f"Source: {citation(run_dir / 'agent_review_judgment_table.csv')}."
        )
        retained = judgments
        if "agent_final_decision" in judgments:
            retained = judgments[judgments["agent_final_decision"].astype(str).ne("discard")]
        for theme, count in top_themes(retained, "review_theme", 5):
            lines.append(f"- Retained theme {readable_label(theme)} appeared in {count} reviewed rows.")

    lines.extend(["", "## Independent exclusion-decision audit", ""])
    if audit_reconciles:
        lines.append(
            f"The independent audit reconciled to the source population: {len(audit)} audited rows for {total} source rows. "
            "That means the discard decisions were checked against the full response population, not only against the first-pass review queue."
        )
    else:
        lines.append(
            f"The independent audit did not reconcile cleanly. It has {len(audit)} rows against {total or 'unknown'} source rows. "
            "This blocks a perfect delivery until the audit is regenerated."
        )
    if discard_count:
        lines.append("The current exclusion-review set is:")
        for _, row in discards.iterrows():
            key = response_key(row)
            rationale = truncate(row.get("agent_discard_rationale") or row.get("semantic_discard_basis") or row.get("observed_evidence"), 320)
            evidence = truncate(row.get("observed_evidence"), 240)
            lines.append(f"- `{key}`: {rationale} Evidence: {evidence} Source: {citation(run_dir / 'agent_discard_set.csv')}.")
    else:
        lines.append("No rows are currently recommended for exclusion review.")
    if missing_packet_rows:
        lines.append(f"Escalation packet mismatch: these discard keys were not found in `agent_escalation_packet.md`: {', '.join(missing_packet_rows)}.")
    else:
        lines.append("The discard set has no detected mismatch against the escalation packet keys when the packet was available.")

    lines.extend(
        [
            "",
            "## Next-pass learning that protects good data",
            "",
            "The next run should improve exclusion discovery without making the review harsher by default. The strongest guardrail is to keep reading the full response chain before removal. Speed, duplicate IP context, keyword mismatch, short wording, and misspellings should route rows to review, but they should not become exclusion evidence unless the chain lacks meaningful context or multiple independent signals converge.",
            "",
            "The positive examples in this report should be reused as calibration anchors. They show the difference between concise but real participation and rows that lack an interpretable answer after the full chain is read.",
            "",
            "## Artifact citations",
            "",
            f"- Quality summary: {run_dir / 'quality_summary.json'}",
            f"- Final judgment table: {run_dir / 'agent_review_judgment_table.csv'}",
            f"- Discard set: {run_dir / 'agent_discard_set.csv'}",
            f"- Full-chain examples: {run_dir / 'full_chain_best_worst_examples.csv'}",
            f"- Independent full-response audit: {run_dir / 'independent_full_response_audit.csv'}",
            f"- Kept review synthesis: {run_dir / 'agent_kept_review_synthesis_table.csv'}",
            f"- Demographic summary: {run_dir / 'demographic_summary.csv'}",
        ]
    )

    out = run_dir / "agent_positive_insights_report.md"
    out.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
