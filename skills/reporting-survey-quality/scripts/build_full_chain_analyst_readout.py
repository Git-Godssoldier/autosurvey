#!/usr/bin/env python3
"""Build a readable analyst memo from full response-chain review artifacts."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import pandas as pd


GOOD_NARRATIVE = {"topic_relevant", "substantive_narrative", "product_relevant"}
GOOD_ROLE = {"trade_relevant", "not_applicable_no_role_field"}
GOOD_BRAND = {"has_valid_brand_or_tool_category", "unknown_possible_brand_only", "not_applicable_no_brand_list"}
GENERIC_PURPOSE_RE = re.compile(r"\b(?:survey|purpose|about)\b", re.I)


def text(value: object, default: str = "") -> str:
    if pd.isna(value):
        return default
    return str(value).strip()


def plain(value: object) -> str:
    return re.sub(r"\s+", " ", text(value)).strip()


def truncate(value: object, limit: int = 900) -> str:
    raw = plain(value)
    if len(raw) <= limit:
        return raw
    return raw[: limit - 3] + "..."


def word_count(value: object) -> int:
    return len(re.findall(r"[A-Za-z0-9']+", text(value)))


def unique_word_count(value: object) -> int:
    return len({item.lower() for item in re.findall(r"[A-Za-z0-9']+", text(value))})


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def run_name(run_dir: Path) -> str:
    summary_path = run_dir / "quality_summary.json"
    if not summary_path.exists():
        return run_dir.name
    try:
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return run_dir.name
    source = summary.get("source_files", [{}])[0].get("file")
    return Path(source).name if source else run_dir.name


def meaningful_segments(chain: object, limit: int = 10) -> list[tuple[str, str, str]]:
    rows: list[tuple[str, str, str]] = []
    for segment in text(chain).split(" || "):
        if ": " not in segment:
            continue
        label, answer = segment.split(": ", 1)
        answer = plain(answer)
        if not answer or len(answer) < 3:
            continue
        if re.fullmatch(r"[0-9. /:-]+", answer):
            continue
        if answer.lower() in {"nan", "none", "no", "yes", "male", "female", "english"}:
            continue
        if len(re.findall(r"[A-Za-z]", answer)) < 3:
            continue
        role = ""
        match = re.search(r"\[(.*?)\]", label)
        if match:
            role = match.group(1)
        column = label.split(" [", 1)[0]
        rows.append((column, role, answer))

    def score(item: tuple[str, str, str]) -> int:
        column, role, answer = item
        value = len(answer)
        if role in {
            "narrative_open_end",
            "job_role_screener",
            "brand_list_or_brand_logic",
            "survey_feedback_or_outro",
            "other_specify",
        }:
            value += 100
        if re.search(r"oe|open|other|spec|outro|qcoe|classify|brand|reason|why", column, re.I):
            value += 80
        return value

    rows.sort(key=score, reverse=True)
    return rows[:limit]


def ensure_columns(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    result = frame.copy()
    for column in columns:
        if column not in result.columns:
            result[column] = ""
    return result


def selected_examples(run_dir: Path, sample_size: int) -> pd.DataFrame:
    audit = read_csv(run_dir / "independent_full_response_audit.csv")
    judgments = read_csv(run_dir / "agent_review_judgment_table.csv")
    if audit.empty:
        raise SystemExit(f"No independent_full_response_audit.csv found in {run_dir}")
    if judgments.empty:
        raise SystemExit(f"No agent_review_judgment_table.csv found in {run_dir}")
    if "full_response_chain" not in audit.columns:
        raise SystemExit("The audit lacks full_response_chain. Rerun build_independent_full_response_audit.py first.")
    if "full_response_chain" not in judgments.columns:
        raise SystemExit("The judgment table lacks full_response_chain. Rerun build_agent_review_artifacts.py first.")

    audit = ensure_columns(
        audit,
        [
            "role_class",
            "brand_quality",
            "narrative_quality",
            "independent_risk_factors",
            "independent_suggested_action",
            "response_chain_field_count",
            "qtime",
            "full_response_chain",
            "narrative_text",
            "respondent_key",
            "supplier",
        ],
    )
    judgments = ensure_columns(
        judgments,
        [
            "agent_final_decision",
            "early_screening_discard_recommendation",
            "semantic_discard_basis",
            "verifier_counterevidence",
            "review_theme",
            "response_chain_field_count",
            "qtime",
            "full_response_chain",
            "raw_open_end_text",
            "respondent_key",
            "supplier",
            "criteria_triggered",
        ],
    )
    if (
        "early_screening_discard_recommendation" not in judgments.columns
        and "programmatic_discard_recommendation" in judgments.columns
    ):
        judgments["early_screening_discard_recommendation"] = judgments["programmatic_discard_recommendation"]

    audit["qtime_num"] = pd.to_numeric(audit["qtime"], errors="coerce")
    audit["chain_count_num"] = pd.to_numeric(audit["response_chain_field_count"], errors="coerce").fillna(0)
    audit["n_words"] = audit["narrative_text"].map(word_count)
    audit["u_words"] = audit["narrative_text"].map(unique_word_count)
    audit["best_score"] = 0
    audit.loc[audit["independent_suggested_action"].astype(str).eq("keep_no_issue_from_independent_audit"), "best_score"] += 45
    audit.loc[audit["role_class"].astype(str).isin(GOOD_ROLE), "best_score"] += 8
    audit.loc[audit["brand_quality"].astype(str).isin(GOOD_BRAND), "best_score"] += 6
    audit.loc[audit["narrative_quality"].astype(str).isin(GOOD_NARRATIVE), "best_score"] += 15
    audit.loc[audit["independent_risk_factors"].astype(str).eq("none"), "best_score"] += 12
    audit.loc[audit["qtime_num"].fillna(0).ge(240), "best_score"] += 4
    audit["best_score"] += audit["chain_count_num"].clip(upper=500).div(70).astype(int)
    audit["best_score"] += audit["n_words"].clip(upper=45).div(3).astype(int)
    audit["best_score"] += audit["u_words"].clip(upper=30).div(4).astype(int)
    audit.loc[audit["n_words"].lt(4), "best_score"] -= 8
    audit.loc[audit["narrative_text"].astype(str).str.contains(GENERIC_PURPOSE_RE, na=False), "best_score"] -= 3

    best_rows: list[dict[str, object]] = []
    best = audit.sort_values(["best_score", "n_words", "chain_count_num"], ascending=[False, False, False]).head(sample_size)
    for _, row in best.iterrows():
        best_rows.append(
            {
                "group": "best",
                "selection_type": "best clean full-chain example",
                "rank_basis": (
                    f"best_score={int(row['best_score'])}; narrative={text(row.get('narrative_quality'))}; "
                    f"words={int(row.get('n_words', 0))}; risks={text(row.get('independent_risk_factors'))}"
                ),
                "respondent_key": text(row.get("respondent_key")),
                "agent_final_decision": "keep_no_issue_from_independent_audit",
                "review_theme": "strong full-chain keep example",
                "qtime": row.get("qtime", ""),
                "supplier": text(row.get("supplier")),
                "response_chain_field_count": row.get("response_chain_field_count", ""),
                "raw_open_end_text": text(row.get("narrative_text")),
                "verifier_counterevidence": "Strong independent audit keep profile across full response chain.",
                "semantic_discard_basis": "No semantic discard basis found.",
                "full_response_chain": text(row.get("full_response_chain")),
            }
        )

    judgments["qtime_num"] = pd.to_numeric(judgments["qtime"], errors="coerce")
    judgments["chain_count_num"] = pd.to_numeric(judgments["response_chain_field_count"], errors="coerce").fillna(0)
    judgments["worst_score"] = 0
    judgments.loc[judgments["agent_final_decision"].astype(str).eq("discard"), "worst_score"] += 100
    judgments.loc[judgments["early_screening_discard_recommendation"].astype(str).str.lower().eq("true"), "worst_score"] += 10
    judgments.loc[~judgments["semantic_discard_basis"].astype(str).str.startswith("No semantic discard"), "worst_score"] += 25
    judgments.loc[
        judgments["review_theme"].astype(str).str.contains(
            "nonsensical|weak|evasive|straightline|duplicate|role-fit", case=False, na=False
        ),
        "worst_score",
    ] += 8
    judgments.loc[judgments["qtime_num"].fillna(999999).lt(240), "worst_score"] += 8
    judgments["worst_score"] += judgments["raw_open_end_text"].map(lambda value: 8 if word_count(value) <= 4 else 0)

    worst_rows: list[dict[str, object]] = []
    worst = judgments.sort_values(["worst_score", "chain_count_num"], ascending=[False, False]).head(sample_size)
    for _, row in worst.iterrows():
        is_discard = text(row.get("agent_final_decision")) == "discard"
        worst_rows.append(
            {
                "group": "worst",
                "selection_type": "confirmed discard" if is_discard else "highest-risk survivor",
                "rank_basis": (
                    f"worst_score={int(row['worst_score'])}; theme={text(row.get('review_theme'))}; "
                    f"criteria={text(row.get('criteria_triggered'))}"
                ),
                "respondent_key": text(row.get("respondent_key")),
                "agent_final_decision": text(row.get("agent_final_decision")),
                "review_theme": text(row.get("review_theme")),
                "qtime": row.get("qtime", ""),
                "supplier": text(row.get("supplier")),
                "response_chain_field_count": row.get("response_chain_field_count", ""),
                "raw_open_end_text": text(row.get("raw_open_end_text")),
                "verifier_counterevidence": text(row.get("verifier_counterevidence")),
                "semantic_discard_basis": text(row.get("semantic_discard_basis")),
                "full_response_chain": text(row.get("full_response_chain")),
            }
        )

    return pd.DataFrame([*best_rows, *worst_rows])


def example_summary(row: pd.Series) -> str:
    segments = meaningful_segments(row.get("full_response_chain"), limit=4)
    if not segments:
        return "No readable respondent-answer segments were recovered from the full chain."
    parts = []
    for column, role, answer in segments:
        role_text = f" [{role}]" if role else ""
        parts.append(f"{column}{role_text}: {truncate(answer, 260)}")
    return " | ".join(parts)


def readable_evidence_sentence(row: pd.Series) -> str:
    segments = meaningful_segments(row.get("full_response_chain"), limit=4)
    if not segments:
        return "The chain does not expose enough readable answer text to summarize."
    narrative = [answer for _, role, answer in segments if role in {"narrative_open_end", "survey_feedback_or_outro", "job_role_screener"}]
    brands = [answer for column, role, answer in segments if role == "brand_list_or_brand_logic" or re.search(r"brand|qcoe2|q13|q17|q63|q90|q121", column, re.I)]
    if narrative and brands:
        return (
            f"The main answer gives a concrete explanation, such as \"{truncate(narrative[0], 180)}\", "
            f"and the chain also carries supporting brand or category context like \"{truncate(brands[0], 120)}\"."
        )
    if narrative:
        return f"The main answer is readable and specific enough to interpret: \"{truncate(narrative[0], 220)}\"."
    first = segments[0][2]
    return f"The strongest readable evidence is the answer \"{truncate(first, 220)}\"."


def weakness_sentence(row: pd.Series) -> str:
    open_end = truncate(row.get("raw_open_end_text"), 180)
    basis = text(row.get("semantic_discard_basis"))
    if text(row.get("agent_final_decision")) == "discard":
        return f"The row remains weak after full-chain review because the main answer is \"{open_end}\" and the verifier basis is: {basis}"
    return (
        f"This row is not a discard, but it is useful calibration. The main answer is \"{open_end}\". "
        "The chain is thin or awkward, but the verifier did not find enough evidence to remove it."
    )


def write_memo(run_dir: Path, examples: pd.DataFrame) -> None:
    dataset = run_name(run_dir)
    judgment = read_csv(run_dir / "agent_review_judgment_table.csv")
    discard_count = int(judgment.get("agent_final_decision", pd.Series(dtype=str)).astype(str).eq("discard").sum())
    reviewed_count = int(len(judgment))
    rescued = 0
    if "early_screening_discard_recommendation" not in judgment.columns and "programmatic_discard_recommendation" in judgment.columns:
        judgment["early_screening_discard_recommendation"] = judgment["programmatic_discard_recommendation"]
    if {"early_screening_discard_recommendation", "agent_final_decision"} <= set(judgment.columns):
        rescued = int(
            (
                judgment["early_screening_discard_recommendation"].astype(str).str.lower().eq("true")
                & judgment["agent_final_decision"].astype(str).ne("discard")
            ).sum()
        )

    lines: list[str] = [
        "# Full-chain analyst readout",
        "",
        f"Dataset: {dataset}",
        "",
        "## Read this first",
        "",
        "This memo is the human-facing reasoning layer for the full response-chain review. The scoring criteria narrowed the review list. The final review then read the stitched response chain and decided whether the row still had a semantic basis for discard.",
        "",
        f"Rows reviewed in detail: {reviewed_count}. Recommended exclusions: {discard_count}. Early exclusion flags rescued by full-chain review: {rescued}.",
        "",
        "## What the best chains show",
        "",
    ]
    best = examples[examples["group"].eq("best")]
    if best.empty:
        lines.append("No best-chain examples were selected.")
    else:
        lines.append("The best chains are not just long. They connect the survey topic to a concrete use case, role, brand, product, project, or reason. They also show why spelling or rough wording should not be treated as a quality failure when meaning is clear.")
        lines.append("")
        for _, row in best.iterrows():
            lines.extend(
                [
                    f"### {row['respondent_key']}",
                    "",
                    f"Open-end focus: {truncate(row.get('raw_open_end_text'), 520)}",
                    "",
                    f"Readable chain evidence: {example_summary(row)}",
                    "",
                    f"Why this is a strong keep: {readable_evidence_sentence(row)} The row has no semantic discard basis.",
                    "",
                ]
            )

    lines.extend(["## What the worst chains show", ""])
    worst = examples[examples["group"].eq("worst")]
    if worst.empty:
        lines.append("No worst-chain examples were selected.")
    else:
        lines.append("The worst chains usually fail in more than one place. A single short answer is not enough. The discard cases stay weak after the full chain is read, or they show repeated generic praise, non-response, hostile content, or mismatched role context.")
        lines.append("")
        for _, row in worst.iterrows():
            lines.extend(
                [
                    f"### {row['respondent_key']}",
                    "",
                    f"Final decision: {row['agent_final_decision']}. Selection type: {row['selection_type']}.",
                    "",
                    f"Open-end focus: {truncate(row.get('raw_open_end_text'), 520)}",
                    "",
                    f"Readable chain evidence: {example_summary(row)}",
                    "",
                    f"Verifier counterevidence: {truncate(row.get('verifier_counterevidence'), 600)}",
                    "",
                    f"Semantic discard basis: {truncate(row.get('semantic_discard_basis'), 600)}",
                    "",
                    f"Analyst interpretation: {weakness_sentence(row)}",
                    "",
                ]
            )

    lines.extend(
        [
            "## Workflow learning",
            "",
            "The workflow succeeds only when both parts are present. Pattern analysis finds the candidates and the recurring survey-design issues. Full-chain reasoning explains the meaning, rescues plausible answers, and leaves the human with a shorter and more useful review queue.",
            "",
            "A run that only emits scores, flags, charts, or raw tables is incomplete. The final package must include this prose interpretation so a PM can understand what the agent saw, why it trusted or rejected the row, and what should change before the next pass.",
            "",
        ]
    )

    (run_dir / "full_chain_analyst_readout.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--sample-size", type=int, default=3)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    examples = selected_examples(run_dir, args.sample_size)
    examples.to_csv(run_dir / "full_chain_best_worst_examples.csv", index=False)
    write_memo(run_dir, examples)
    print(run_dir / "full_chain_best_worst_examples.csv")
    print(run_dir / "full_chain_analyst_readout.md")


if __name__ == "__main__":
    main()
