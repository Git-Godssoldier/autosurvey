#!/usr/bin/env python3
"""Build a transferable discard rulebook from TFG status-labeled workbooks."""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd


ACCEPTED_STATUS = "3"
REJECTED_STATUS = "5"

TECHNICAL_RE = re.compile(
    r"record|uuid|rid|date|markers|status|rd_|gettoken|source|supplier|vendor|supname|url|"
    r"useragent|session|email|closingemail|dcua|bhf|sfh|state|city|zip|region|country|province|"
    r"dma|vbrowser|vmobile|^list$|conditions|quota|langassess|validclient|qtime",
    re.I,
)
OPEN_END_RE = re.compile(r"oe$|outro|open|comment|explain|why|other|specify|qcoe|_pasted$", re.I)
MATRIX_RE = re.compile(r"(.+?)(?:_L)?r\d+r\d+$|(.+?)r\d+$", re.I)
PLACEHOLDER_RE = re.compile(
    r"^(n/?a|na|none|nothing|no|nope|idk|i don'?t know|dont know|not sure|unsure|good|ok|okay|"
    r"yes|test|asdf|blah|nil|not applicable|no comment|no idea|nothing else|none at all)[.! ]*$",
    re.I,
)
SURVEY_FEEDBACK_RE = re.compile(r"\b(survey|questionnaire|questions|this study|this survey|asked me)\b", re.I)
AI_MARKER_RE = re.compile(
    r"\b(as an ai|language model|cannot answer|i do not have personal experience|comprehensive|seamless|"
    r"innovative solution|valuable insight|user-friendly|efficient and effective|significantly enhance)\b",
    re.I,
)
HOSTILE_OR_NONSENSE_RE = re.compile(r"\b(fuck|shit|stupid|idiot|asdf|qwerty|blah|gibberish)\b", re.I)


@dataclass(frozen=True)
class Rule:
    rule_id: str
    name: str
    family: str
    transfer_role: str
    description: str
    use_on_unannotated_data: str
    guardrail: str


RULES = [
    Rule(
        "speed_under_4_minutes",
        "Very fast completion under 4 minutes",
        "timing",
        "review_routing",
        "The respondent completed the survey in less than 240 seconds.",
        "Route for review. Escalate only when the response chain is also weak, contradictory, copied, or generic.",
        "Many real respondents can be fast. Speed alone is not a final discard reason.",
    ),
    Rule(
        "speed_4_to_5_minutes",
        "Fast completion from 4 to 5 minutes",
        "timing",
        "context_signal",
        "The respondent completed the survey in 240 to 299 seconds.",
        "Use as context and compare against answer depth.",
        "Do not escalate unless another authenticity signal confirms it.",
    ),
    Rule(
        "platform_termflag",
        "Platform termination or quality flag",
        "platform_quality",
        "candidate_discard_signal",
        "A platform helper field such as TERMFLAGS is nonzero.",
        "Treat as strong routing evidence, then verify with the full response chain.",
        "Confirm the field meaning from the Datamap or export before using it on a new client.",
    ),
    Rule(
        "platform_scrutinyflag",
        "Platform scrutiny flag",
        "platform_quality",
        "candidate_discard_signal",
        "A platform helper field such as SCRUTINYFLAGS is nonzero.",
        "Treat as strong routing evidence, then verify with the full response chain.",
        "Some scrutiny flags can appear in accepted rows. Use accepted examples as guardrails.",
    ),
    Rule(
        "research_defender_nonzero_review",
        "Research Defender review signal",
        "platform_quality",
        "review_routing",
        "A Research Defender open-end review helper field is nonzero.",
        "Use as review routing and inspect the associated text field.",
        "Research Defender signals are context. They are not final proof of fabrication.",
    ),
    Rule(
        "required_open_end_placeholder",
        "Placeholder or direct non-answer in an open end",
        "open_end_authenticity",
        "candidate_discard_signal",
        "A substantive open end contains a direct placeholder such as none, idk, not sure, or no comment.",
        "Escalate when the prompt required a substantive answer and the full chain does not recover context.",
        "Do not penalize true other-specify fields where no text was required.",
    ),
    Rule(
        "required_open_end_too_short",
        "Very short open end where depth was expected",
        "open_end_authenticity",
        "review_routing",
        "A key open end has only one or two words.",
        "Review against the prompt. Escalate only if the field asked for explanation or experience.",
        "Short brands, locations, products, or factor lists can be valid.",
    ),
    Rule(
        "copied_open_end",
        "Copied or repeated open-end text",
        "duplication",
        "candidate_discard_signal",
        "The same normalized open-end text appears in multiple supposedly independent rows.",
        "Escalate when the copied answer appears in a substantive field and is paired with other weak signals.",
        "Common short answers can repeat naturally. Require meaningful duplicate text.",
    ),
    Rule(
        "pasted_text_helper",
        "Pasted text helper flag",
        "open_end_authenticity",
        "review_routing",
        "A pasted-text helper field is nonzero.",
        "Review the pasted answer and compare it against the prompt.",
        "Pasting can be benign if a respondent drafts elsewhere. Use with semantic context.",
    ),
    Rule(
        "survey_feedback_in_substantive_field",
        "Survey feedback instead of substantive answer",
        "open_end_authenticity",
        "review_routing",
        "The response comments on the survey or questions instead of answering the substantive prompt.",
        "Escalate when the full chain shows the respondent repeatedly avoids the actual study topic.",
        "Some outro prompts invite survey feedback. Confirm the prompt before escalating.",
    ),
    Rule(
        "ai_or_overpolished_generic_text",
        "AI-like or over-polished generic prose",
        "llm_suspicion",
        "review_routing",
        "The text uses generic, polished, non-specific phrasing that can signal LLM assistance.",
        "Use as a suspicion signal. Escalate only with contradiction, weak chain, duplication, or timing evidence.",
        "A fluent respondent can write polished prose. Specific lived detail weakens this signal.",
    ),
    Rule(
        "hostile_or_nonsense_text",
        "Hostile, nonsense, or keyboard-mash text",
        "open_end_authenticity",
        "candidate_discard_signal",
        "A substantive answer contains hostile language, nonsense, or keyboard-mash text.",
        "Escalate when the answer cannot be read as meaningful in context.",
        "Do not over-penalize casual tone if the answer is otherwise coherent.",
    ),
    Rule(
        "matrix_near_straightline",
        "Near-straightlined matrix",
        "attention",
        "review_routing",
        "At least 90 percent of answered matrix cells in a group use the same value.",
        "Use as review routing and compare with the full chain.",
        "Uniform ratings can be a real opinion. This is weak by itself.",
    ),
    Rule(
        "long_low_specificity_text",
        "Long answer with low specificity",
        "llm_suspicion",
        "review_routing",
        "A long open-end answer repeats generic concepts and has low lexical variety.",
        "Review for LLM-like filler and lack of personal or project-specific detail.",
        "Long text is not bad by itself. Specific detail can make it credible.",
    ),
    Rule(
        "internal_inconsistency_numeric_allocations",
        "Suspicious numeric allocation pattern",
        "consistency",
        "context_signal",
        "Many allocation fields use repeated round or equal values across unrelated questions.",
        "Use as context with straightlining and response-chain review.",
        "Some tasks ask for allocations that naturally sum to round numbers.",
    ),
    Rule(
        "semantic_abstract_business_no_lived_detail",
        "Abstract business solution without lived detail",
        "semantic_authenticity",
        "agent_semantic_rule",
        "The response uses plausible business language but does not sound like a respondent describing their own work.",
        "Route to semantic review when a prompt asks for lived experience, operational pain, or a concrete example.",
        "Keep when the full chain has concrete role, project, material, supplier, location, or decision detail.",
    ),
    Rule(
        "semantic_survey_meta_answer",
        "Survey meta-analysis instead of respondent answer",
        "semantic_authenticity",
        "agent_semantic_rule",
        "The response describes what the survey or poll measured instead of answering as a respondent.",
        "Escalate when the field asked for the respondent's own reason, experience, or preference.",
        "Some outro prompts invite survey feedback. Confirm the prompt before escalating.",
    ),
    Rule(
        "semantic_role_or_qualification_mismatch",
        "Role or qualification mismatch",
        "semantic_authenticity",
        "agent_semantic_rule",
        "The open ends sound like a respondent outside the intended qualified audience.",
        "Compare open ends against role, trade, industry, purchase authority, and project-involvement fields.",
        "A qualified respondent can discuss personal projects. Keep when the full chain proves role fit.",
    ),
    Rule(
        "semantic_personal_home_project_in_trade_context",
        "Personal-home project substituted for professional project",
        "semantic_authenticity",
        "agent_semantic_rule",
        "A trade or building-material survey receives consumer home, decor, appliance, or household-accent examples.",
        "Route to semantic review when the survey expects professional trade, contractor, dealer, or project context.",
        "This is not a discard signal when the survey explicitly allows homeowner or DIY respondents.",
    ),
    Rule(
        "semantic_generic_project_claim",
        "Fluent but generic project claim",
        "semantic_authenticity",
        "agent_semantic_rule",
        "The answer sounds polished but lacks credible process detail after a concrete-example prompt.",
        "Review for missing materials, constraints, trade role, timeline, tools, suppliers, or customer context.",
        "Polished writing is acceptable when it includes specific lived detail.",
    ),
    Rule(
        "semantic_sentence_drift",
        "Sentence drift and incoherent phrase chaining",
        "semantic_authenticity",
        "agent_semantic_rule",
        "The answer begins plausibly but drifts into unrelated or incoherent phrase chains.",
        "Escalate when the full chain cannot recover a meaningful answer.",
        "Rough grammar is not enough. The issue is loss of interpretable meaning.",
    ),
    Rule(
        "semantic_list_when_use_case_required",
        "List answer where a use case was required",
        "semantic_authenticity",
        "agent_semantic_rule",
        "The answer gives a bare list of objects or places where the prompt asked for a use case or explanation.",
        "Inspect the prompt role and route for semantic review.",
        "Lists are valid when the prompt asks for locations, brands, products, or factors.",
    ),
    Rule(
        "semantic_off_domain_professional_claim",
        "Off-domain professional claim",
        "semantic_authenticity",
        "agent_semantic_rule",
        "The answer describes a coherent professional activity that belongs to the wrong respondent universe.",
        "Use after field-role mapping identifies the intended respondent universe.",
        "Do not use until role and qualification fields are mapped.",
    ),
]


def text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def normalized_status(value: object) -> str:
    raw = text(value)
    if raw.endswith(".0"):
        raw = raw[:-2]
    return raw


def normalize_answer(value: object) -> str:
    raw = re.sub(r"\s+", " ", text(value).lower()).strip()
    raw = re.sub(r"[^a-z0-9' ]+", "", raw)
    return raw.strip()


def word_count(value: object) -> int:
    return len(re.findall(r"[A-Za-z']+", text(value)))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Annotated .xlsx, .zip, or directory.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sheet", default="A1")
    parser.add_argument("--id-column", default="uuid")
    parser.add_argument("--min-duplicate-length", type=int, default=16)
    parser.add_argument("--example-limit", type=int, default=8)
    return parser.parse_args()


def workbook_entries(path: Path) -> list[tuple[str, bytes]]:
    path = path.expanduser().resolve()
    if path.is_dir():
        entries: list[tuple[str, bytes]] = []
        for child in sorted(path.rglob("*")):
            if child.suffix.lower() in {".xlsx", ".zip"}:
                entries.extend(workbook_entries(child))
        return entries
    if path.suffix.lower() == ".xlsx":
        return [(path.name, path.read_bytes())]
    if path.suffix.lower() == ".zip":
        entries = []
        with ZipFile(path) as zf:
            for name in zf.namelist():
                lower = name.lower()
                if lower.endswith(".xlsx"):
                    entries.append((name, zf.read(name)))
                elif lower.endswith(".zip"):
                    with ZipFile(BytesIO(zf.read(name))) as nested:
                        for nested_name in nested.namelist():
                            if nested_name.lower().endswith(".xlsx"):
                                entries.append((f"{name}::{nested_name}", nested.read(nested_name)))
        return entries
    raise SystemExit(f"Unsupported input type: {path}")


def read_workbook(entry_name: str, data: bytes, sheet: str) -> pd.DataFrame:
    try:
        return pd.read_excel(BytesIO(data), sheet_name=sheet, engine="openpyxl")
    except ValueError:
        return pd.read_excel(BytesIO(data), sheet_name=0, engine="openpyxl")
    except Exception as exc:
        raise SystemExit(f"Could not read {entry_name}: {exc}") from exc


def open_end_columns(df: pd.DataFrame) -> list[str]:
    cols: list[str] = []
    for col in df.columns:
        name = text(col)
        if not name or TECHNICAL_RE.search(name):
            continue
        series = df[col].dropna().map(text)
        if series.empty:
            continue
        avg_len = series.str.len().mean()
        if OPEN_END_RE.search(name) or avg_len >= 18:
            cols.append(name)
    return cols


def matrix_groups(df: pd.DataFrame) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for col in df.columns:
        name = text(col)
        if not name or TECHNICAL_RE.search(name):
            continue
        match = MATRIX_RE.match(name)
        if not match:
            continue
        prefix = next(part for part in match.groups() if part)
        groups[prefix].append(name)
    return {prefix: cols for prefix, cols in groups.items() if len(cols) >= 8}


def duplicate_values(df: pd.DataFrame, cols: list[str], min_len: int) -> dict[str, set[str]]:
    output: dict[str, set[str]] = {}
    for col in cols:
        counts = Counter(
            value
            for value in df[col].map(normalize_answer)
            if len(value) >= min_len and not PLACEHOLDER_RE.match(value)
        )
        output[col] = {value for value, count in counts.items() if count >= 2}
    return output


def matrix_straightline_rows(df: pd.DataFrame) -> set[int]:
    rows: set[int] = set()
    for cols in matrix_groups(df).values():
        numeric = df[cols].apply(pd.to_numeric, errors="coerce")
        counts = numeric.notna().sum(axis=1)
        same_share = numeric.apply(lambda row: row.value_counts(dropna=True).max() / row.count() if row.count() else 0, axis=1)
        rows.update(int(idx) for idx in df.index[(counts >= 8) & (same_share >= 0.9)])
    return rows


def numeric_allocation_pattern(row: pd.Series) -> bool:
    numeric_values: list[float] = []
    for col, value in row.items():
        name = text(col)
        if TECHNICAL_RE.search(name):
            continue
        if not re.search(r"r\d+$", name):
            continue
        parsed = pd.to_numeric(value, errors="coerce")
        if pd.notna(parsed):
            numeric_values.append(float(parsed))
    if len(numeric_values) < 12:
        return False
    rounded = [value for value in numeric_values if value in {0, 10, 20, 25, 33, 34, 50, 90, 95, 100}]
    return len(rounded) / len(numeric_values) >= 0.75


def row_rule_hits(row: pd.Series, open_cols: list[str], duplicates: dict[str, set[str]], straightline_rows: set[int]) -> dict[str, list[str]]:
    hits: dict[str, list[str]] = defaultdict(list)
    qtime = pd.to_numeric(row.get("qtime"), errors="coerce") if "qtime" in row.index else math.nan
    if pd.notna(qtime):
        if qtime < 240:
            hits["speed_under_4_minutes"].append(f"qtime={qtime:.1f}")
        elif qtime < 300:
            hits["speed_4_to_5_minutes"].append(f"qtime={qtime:.1f}")

    for col, value in row.items():
        name = text(col)
        raw = text(value)
        if not raw or raw in {"0", "0.0", "low", "English"}:
            continue
        if re.search(r"TERMFLAGS", name, re.I):
            hits["platform_termflag"].append(f"{name}={raw}")
        if re.search(r"SCRUTINYFLAGS", name, re.I):
            hits["platform_scrutinyflag"].append(f"{name}={raw}")
        if re.search(r"RD_Review", name, re.I) and raw not in {"0", "0.0"}:
            hits["research_defender_nonzero_review"].append(f"{name}={raw}")
        if re.search(r"_Pasted$", name, re.I) and raw not in {"0", "0.0"}:
            hits["pasted_text_helper"].append(f"{name}={raw}")

    for col in open_cols:
        value = text(row.get(col))
        if not value:
            continue
        normalized = normalize_answer(value)
        words = word_count(value)
        if PLACEHOLDER_RE.match(value):
            hits["required_open_end_placeholder"].append(f"{col}: {value[:80]}")
        if words <= 2 and re.search(r"oe$|outro|qcoe", col, re.I):
            hits["required_open_end_too_short"].append(f"{col}: {value[:80]}")
        if normalized in duplicates.get(col, set()):
            hits["copied_open_end"].append(f"{col}: {value[:80]}")
        if SURVEY_FEEDBACK_RE.search(value) and re.search(r"qcoe|outro|oe$", col, re.I):
            hits["survey_feedback_in_substantive_field"].append(f"{col}: {value[:80]}")
        if AI_MARKER_RE.search(value) or "—" in value:
            hits["ai_or_overpolished_generic_text"].append(f"{col}: {value[:80]}")
        if HOSTILE_OR_NONSENSE_RE.search(value):
            hits["hostile_or_nonsense_text"].append(f"{col}: {value[:80]}")
        if words >= 45:
            unique_ratio = len(set(re.findall(r"[A-Za-z']+", value.lower()))) / max(words, 1)
            if unique_ratio < 0.55:
                hits["long_low_specificity_text"].append(f"{col}: {value[:80]}")

    if int(row.name) in straightline_rows:
        hits["matrix_near_straightline"].append("one or more matrix groups use the same value in at least 90% of answered cells")
    if numeric_allocation_pattern(row):
        hits["internal_inconsistency_numeric_allocations"].append("many allocation or rating fields use repeated round values")
    return dict(hits)


def row_excerpt(row: pd.Series, open_cols: list[str], limit: int = 500) -> str:
    parts = []
    for col in open_cols:
        value = text(row.get(col))
        if value:
            parts.append(f"{col}: {value}")
    return " | ".join(parts)[:limit]


def derive(entry_name: str, data: bytes, args: argparse.Namespace):
    df = read_workbook(entry_name, data, args.sheet)
    df.columns = [text(col) for col in df.columns]
    if "status" not in df.columns:
        return [], [], [], {
            "dataset": entry_name,
            "rows": len(df),
            "has_status": False,
            "note": "No status column. Treat as blinded test data.",
        }
    df["__status"] = df["status"].map(normalized_status)
    labeled = df[df["__status"].isin({ACCEPTED_STATUS, REJECTED_STATUS})].copy()
    open_cols = open_end_columns(labeled)
    duplicates = duplicate_values(labeled, open_cols, args.min_duplicate_length)
    straightline_rows = matrix_straightline_rows(labeled)
    id_col = args.id_column if args.id_column in labeled.columns else next(
        (candidate for candidate in ["uuid", "record", "RID"] if candidate in labeled.columns),
        "",
    )

    rejected_rows = []
    accepted_guardrail_rows = []
    counts: dict[str, Counter[str]] = defaultdict(Counter)
    examples: dict[str, dict[str, list[dict[str, object]]]] = defaultdict(lambda: {"rejected": [], "accepted": []})
    for idx, row in labeled.iterrows():
        status = row["__status"]
        hits = row_rule_hits(row, open_cols, duplicates, straightline_rows)
        for rule_id, evidence in hits.items():
            counts[rule_id][status] += 1
            bucket = "rejected" if status == REJECTED_STATUS else "accepted"
            if len(examples[rule_id][bucket]) < args.example_limit:
                examples[rule_id][bucket].append(
                    {
                        "dataset": entry_name,
                        "source_row_number": int(idx) + 2,
                        "respondent_key": text(row.get(id_col)) if id_col else str(idx + 2),
                        "status": status,
                        "evidence": "; ".join(evidence[:4]),
                        "open_end_excerpt": row_excerpt(row, open_cols),
                    }
                )
        row_record = {
            "dataset": entry_name,
            "source_row_number": int(idx) + 2,
            "respondent_key": text(row.get(id_col)) if id_col else str(idx + 2),
            "status": status,
            "qtime": row.get("qtime", ""),
            "rule_count": len(hits),
            "rules": "; ".join(sorted(hits)),
            "evidence": " | ".join(f"{rule}: {'; '.join(values[:3])}" for rule, values in sorted(hits.items())),
            "open_end_excerpt": row_excerpt(row, open_cols),
        }
        if status == REJECTED_STATUS:
            rejected_rows.append(row_record)
        elif hits:
            accepted_guardrail_rows.append(row_record)

    accepted = int((labeled["__status"] == ACCEPTED_STATUS).sum())
    rejected = int((labeled["__status"] == REJECTED_STATUS).sum())
    base_rate = rejected / max(accepted + rejected, 1)
    rule_rows = []
    for rule in RULES:
        accepted_hits = counts[rule.rule_id][ACCEPTED_STATUS]
        rejected_hits = counts[rule.rule_id][REJECTED_STATUS]
        support = accepted_hits + rejected_hits
        reject_rate = rejected_hits / support if support else 0
        if support == 0:
            role = "not_observed"
        elif support < 10:
            role = "needs_more_examples"
        elif reject_rate >= max(0.6, base_rate * 1.75):
            role = "candidate_discard_signal"
        elif reject_rate <= min(0.2, base_rate * 0.55):
            role = "false_positive_guardrail"
        else:
            role = rule.transfer_role
        rule_rows.append(
            {
                "dataset": entry_name,
                "rule_id": rule.rule_id,
                "name": rule.name,
                "family": rule.family,
                "accepted_hits": accepted_hits,
                "rejected_hits": rejected_hits,
                "support_rows": support,
                "reject_rate_when_rule_fires": round(reject_rate, 4),
                "dataset_reject_rate": round(base_rate, 4),
                "observed_transfer_role": role,
                "rulebook_transfer_role": rule.transfer_role,
                "description": rule.description,
                "use_on_unannotated_data": rule.use_on_unannotated_data,
                "guardrail": rule.guardrail,
                "rejected_examples_json": json.dumps(examples[rule.rule_id]["rejected"], ensure_ascii=True),
                "accepted_examples_json": json.dumps(examples[rule.rule_id]["accepted"], ensure_ascii=True),
            }
        )
    summary = {
        "dataset": entry_name,
        "rows": len(df),
        "has_status": True,
        "accepted_status_3": accepted,
        "rejected_status_5": rejected,
        "reject_rate": round(base_rate, 4),
        "rejected_rows_with_no_script_rule": sum(1 for row in rejected_rows if not row["rules"]),
        "open_end_columns": len(open_cols),
        "id_column": id_col,
    }
    return rejected_rows, accepted_guardrail_rows, rule_rows, summary


def write_markdown(output_dir: Path, summaries: list[dict[str, object]], rule_df: pd.DataFrame) -> None:
    labeled = [row for row in summaries if row.get("has_status")]
    accepted = sum(int(row.get("accepted_status_3", 0)) for row in labeled)
    rejected = sum(int(row.get("rejected_status_5", 0)) for row in labeled)
    no_rule = sum(int(row.get("rejected_rows_with_no_script_rule", 0)) for row in labeled)
    lines = [
        "# TFG discard signal rulebook",
        "",
        "This rulebook is derived from the client-provided status-labeled datasets.",
        "`status = 3` means TFG accepted the respondent.",
        "`status = 5` means TFG rejected the respondent for quality or authenticity concerns.",
        "The status label trains client-rejection probability. It does not prove that every rejected respondent is fraudulent, bot-like, or LLM-generated.",
        "The rules below are evidence prompts for agent review. They must be tested against accepted-row guardrails before they become exclusion logic.",
        "",
        "The goal is to transfer TFG's rejection logic into autosurvey for unannotated datasets.",
        "The rules below are not blind automation. They are evidence families for agent review.",
        "",
        f"Labeled respondents: {accepted + rejected}",
        f"Accepted status 3: {accepted}",
        f"Rejected status 5: {rejected}",
        f"Rejected rows with no script-staged rule: {no_rule}",
        "",
        "## Dataset coverage",
        "",
    ]
    for row in labeled:
        lines.append(
            f"- {row['dataset']}: {row['rejected_status_5']} rejected, {row['accepted_status_3']} accepted, "
            f"{row['reject_rate'] * 100:.1f}% rejected, {row['rejected_rows_with_no_script_rule']} rejected rows with no script-staged rule."
        )
    lines.extend(["", "## Transfer rules", ""])
    grouped = (
        rule_df.groupby("rule_id")
        .agg(
            name=("name", "first"),
            family=("family", "first"),
            accepted_hits=("accepted_hits", "sum"),
            rejected_hits=("rejected_hits", "sum"),
            support_rows=("support_rows", "sum"),
            use_on_unannotated_data=("use_on_unannotated_data", "first"),
            guardrail=("guardrail", "first"),
        )
        .reset_index()
    )
    grouped["reject_rate"] = grouped["rejected_hits"] / grouped["support_rows"].where(grouped["support_rows"] != 0, 1)
    grouped = grouped.sort_values(["rejected_hits", "reject_rate"], ascending=[False, False])
    for _, row in grouped.iterrows():
        lines.extend(
            [
                f"### {row['name']}",
                "",
                f"- Rule id: `{row['rule_id']}`",
                f"- Family: {row['family']}",
                f"- Rejected hits: {int(row['rejected_hits'])}",
                f"- Accepted counterexamples: {int(row['accepted_hits'])}",
                f"- Rejection rate when present: {row['reject_rate'] * 100:.1f}%",
                f"- How to use on unannotated data: {row['use_on_unannotated_data']}",
                f"- Guardrail: {row['guardrail']}",
                "",
            ]
        )
    lines.extend(
        [
            "## Required agent step",
            "",
            "Every rejected row is present in `tfg_rejected_row_rule_ledger.csv`.",
            "Every accepted row that fired one of these rules is present in `tfg_accepted_guardrail_ledger.csv`.",
            "The agent must read the semantic packets and write packet notes before promoting a rule from review routing into discard escalation.",
            "Rows with no script-staged rule are especially important. They show where semantic understanding must discover patterns the current parser missed.",
            "",
        ]
    )
    (output_dir / "tfg_discard_signal_rulebook.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = args.output_dir.expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    all_rejected: list[dict[str, object]] = []
    all_accepted_guardrails: list[dict[str, object]] = []
    all_rules: list[dict[str, object]] = []
    summaries: list[dict[str, object]] = []
    for entry_name, data in workbook_entries(args.input):
        rejected, accepted_guardrails, rules, summary = derive(entry_name, data, args)
        summaries.append(summary)
        all_rejected.extend(rejected)
        all_accepted_guardrails.extend(accepted_guardrails)
        all_rules.extend(rules)

    rejected_df = pd.DataFrame(all_rejected)
    guardrail_df = pd.DataFrame(all_accepted_guardrails)
    rule_df = pd.DataFrame(all_rules)
    summary_df = pd.DataFrame(summaries)
    rejected_df.to_csv(output_dir / "tfg_rejected_row_rule_ledger.csv", index=False)
    if not rejected_df.empty:
        rejected_df[rejected_df["rules"].fillna("").eq("")].to_csv(
            output_dir / "tfg_rejected_semantic_discovery_backlog.csv",
            index=False,
        )
    else:
        pd.DataFrame().to_csv(output_dir / "tfg_rejected_semantic_discovery_backlog.csv", index=False)
    guardrail_df.to_csv(output_dir / "tfg_accepted_guardrail_ledger.csv", index=False)
    rule_df.to_csv(output_dir / "tfg_discard_rule_evidence.csv", index=False)
    summary_df.to_csv(output_dir / "tfg_discard_rulebook_dataset_summary.csv", index=False)
    write_markdown(output_dir, summaries, rule_df)
    print(output_dir / "tfg_discard_signal_rulebook.md")


if __name__ == "__main__":
    main()
