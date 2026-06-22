#!/usr/bin/env python3
"""Audit every source row independently and compare the audit to autosurvey outputs."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import pandas as pd


TRADE_TERMS = re.compile(
    r"construction|contract|handyman|plumb|electric|hvac|carpenter|carpentry|remodel|renovat|paint|painter|"
    r"mason|masonry|concrete|framer|framing|roof|roofing|drywall|floor|tile|cabinet|woodwork|builder|build|"
    r"home repair|repair|maintenance|landscap|lawn|hardscape|fence|deck|window|door|property repairs|"
    r"real estate construction|developer|architect|solar installation|heating|cooling|foreman|supervisor|"
    r"crew|jobsite|millwork|finish work|epoxy flooring|fire suppression|blue collar|oilfield|pipe fitter|"
    r"steel framing|brick|home improvement|residential|commercial|property operations|property manager|"
    r"rental|apartments|site foreman|welding|welder|equipment operator|snow removal|exterminator|"
    r"fabrication|install|installer",
    re.I,
)
MAYBE_ROLE_TERMS = re.compile(
    r"operations|manager|director|owner|business|oversee|project manager|raw material|purchases|employees|"
    r"real estate|property|side work|odd jobs|yard work|consultant|investor|decision-maker|ceo|lead man",
    re.I,
)
NON_TRADE_TERMS = re.compile(
    r"delivery|packages|tik tok|tiktok|uber|doordash|door dash|insta cart|lyft|mcdonald|barista|cafe|"
    r"nurse|lab|data entry|music|musician|graphic designer|software engineer|write code|tech company|"
    r"customer service|freelance writing|tattoo|hr manager|human resources|it director|director of it|"
    r"real estate agent|etsy|youtube|unemployed|not too sure|paid studies|offerup|flip items|dog grooming|"
    r"food|restaurants|retired|injury",
    re.I,
)
ABUSIVE_TERMS = re.compile(r"fuck|shit|piece[s]? of shit|no\\. no\\. fuck", re.I)
BRAND_TERMS = re.compile(
    r"dewalt|de walt|dew|dwalt|dewaly|dwar|stanley|black\\s*(and|&)\\s*decker|black n decker|"
    r"craftsman|craftmen|milwaukee|milwalkie|milwakee|makita|makia|malika|nikita|ryobi|riobi|"
    r"robi|bosch|boch|porter\\s*cable|skil|skill|ridgid|rigid|kobalt|kobolt|husky|hilti|cat|"
    r"caterpillar|wen|lg|ge|stihl|sthl|snap|matco|klein|hercules|bauer|festool|metabo|"
    r"masterforce|hart|hitachi|bostitch|bobcat|grainger|lowe|home depot|procore|kline|stabila|"
    r"sears|huskvarna|trupper|fein|flex|green works|greenworks",
    re.I,
)
TOOL_CATEGORY_TERMS = re.compile(r"saw|drill|nail gun|oscillator|tape measure|power drill|tool|tools|hammer|level|ladder|battery|impact|driver", re.I)
INVALID_BRAND_TERMS = re.compile(r"^(no|none|all|dot|human|huffy|nickerson|yamuke|hyperguy|eleganzer|fusion|menace|bower|yougfin)$", re.I)
SUBSTANTIVE_FACTOR_TERMS = re.compile(
    r"cost|price|afford|value|quality|durab|reliab|fit|function|feature|design|style|look|brand|"
    r"safety|security|privacy|comfort|convenien|easy|ease|efficient|energy|warrant|service|support|"
    r"install|maintain|maintenance|material|size|color|performance|availability|speed|taste|clean|"
    r"location|staff|employee|experience|selection|variety|technology|smart|access|trust|recommend",
    re.I,
)
GENERIC_SURVEY_FEEDBACK_TERMS = re.compile(
    r"interesting|great survey|good survey|nice survey|very good|good question|i like the idea|i liked the idea|"
    r"learned|informative|experience|topic",
    re.I,
)
NON_COOPERATIVE_NARRATIVE_TERMS = re.compile(
    r"do not know|don't know|dont know|no idea|nothing|none|n/?a|not sure|would change nothing|"
    r"prefer not|skip|asdf|test",
    re.I,
)


def text(value: object, default: str = "") -> str:
    if pd.isna(value):
        return default
    return str(value).strip()


def chain_text(value: object, limit: int = 900) -> str:
    raw = re.sub(r"\s+", " ", text(value))
    if len(raw) > limit:
        return raw[: limit - 3] + "..."
    return raw


def truthy(value: object) -> bool:
    if isinstance(value, bool):
        return value
    return text(value).lower() not in {"false", "0", "no", "n", ""}


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def source_workbook(run_dir: Path) -> Path:
    summary_path = run_dir / "quality_summary.json"
    if not summary_path.exists():
        raise SystemExit(f"No quality_summary.json found in {run_dir}")
    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    source_files = summary.get("source_files", [])
    if not source_files:
        raise SystemExit(f"No source files listed in {summary_path}")
    return Path(source_files[0]["file"])


def run_summary(run_dir: Path) -> dict:
    summary_path = run_dir / "quality_summary.json"
    if not summary_path.exists():
        return {}
    return json.loads(summary_path.read_text(encoding="utf-8"))


def topic_pattern(summary: dict) -> re.Pattern[str] | None:
    keywords: list[str] = []
    for profile in summary.get("discovery_profiles", {}).values():
        keywords.extend(str(item) for item in profile.get("topic_keywords", []) if str(item).strip())
    keywords = sorted(set(keywords), key=len, reverse=True)
    if not keywords:
        return None
    return re.compile("|".join(re.escape(item) for item in keywords), re.I)


def fallback_field_role(column: str, summary: dict) -> str:
    lower = column.lower()
    open_end_cols = set(open_end_columns_from_summary(summary))
    matrix_cols = {
        item
        for profile in summary.get("discovery_profiles", {}).values()
        for cols in profile.get("matrix_groups", {}).values()
        for item in cols
    }
    brand_cols = {
        item
        for profile in summary.get("discovery_profiles", {}).values()
        for item in profile.get("brand_consistency_candidate_columns", [])
    }
    if re.search(r"uuid|^record$|^rid$|session", lower):
        return "respondent_identifier"
    if re.search(r"^(date|start_date|start_time|started_at|timestamp)$|start.?date|start.?time", lower):
        return "fielding_timestamp"
    if re.search(r"qtime|duration|elapsed|time", lower):
        return "timing_field"
    if re.search(r"ipaddress|ip_|device|browser|useragent", lower):
        return "ip_or_device_field"
    if re.search(r"supname|supplier|source|vendor", lower):
        return "supplier_or_source_field"
    if TECHNICAL_TEXT_FIELD_TERMS.search(column):
        return "technical_or_hidden_field"
    if column in matrix_cols:
        return "matrix_grid"
    if re.search(r"^(qgender|qager1|qage|age|qethnic(?:r\d+(?:oe)?)?|qed|qstatever|qemploy|qushhi|q44|q45|qpolitics)$", lower):
        return "demographic_field"
    if re.search(r"qcoe1|qindustry|qtrade|classify|occupation|job|role", lower):
        return "job_role_screener"
    if column in brand_cols or re.search(r"brand|aware|prefer|consider|recommend|purchase", lower):
        return "brand_list_or_brand_logic"
    if re.search(r"other|specify", lower):
        return "other_specify"
    if re.search(r"feedback|outro", lower):
        return "survey_feedback_or_outro"
    if column in open_end_cols:
        return "narrative_open_end"
    return "respondent_answer"


def load_question_chain_map(run_dir: Path, source: pd.DataFrame, workbook_name: str, sheet_name: str, summary: dict) -> pd.DataFrame:
    path = run_dir / "question_chain_map.csv"
    if path.exists():
        chain = pd.read_csv(path)
        if "source_workbook" in chain.columns:
            scoped = chain[chain["source_workbook"].astype(str).eq(workbook_name)].copy()
            if not scoped.empty:
                return scoped
        if not chain.empty:
            return chain.copy()

    rows: list[dict[str, object]] = []
    for position, column in enumerate((str(item) for item in source.columns), start=1):
        role = fallback_field_role(column, summary)
        rows.append(
            {
                "source_workbook": workbook_name,
                "sheet": sheet_name,
                "position": position,
                "source_column": column,
                "field_role": role,
                "question_text": column,
                "include_in_full_response_chain": role not in CHAIN_EXCLUDED_ROLES,
                "include_in_focused_semantic_chain": bool(re.search(r"^(qcoe1|q9|q9r10oe|pipeintoq10|q10|q32|q43|outro)", column, re.I)),
            }
        )
    return pd.DataFrame(rows)


def response_chain(row: pd.Series, question_chain: pd.DataFrame, include_column: str) -> tuple[str, int]:
    pieces: list[str] = []
    for _, field in question_chain.sort_values("position").iterrows():
        if not truthy(field.get(include_column, True)):
            continue
        column = text(field.get("source_column"))
        if column not in row.index:
            continue
        answer = chain_text(row.get(column))
        if not answer:
            continue
        role = text(field.get("field_role"), "respondent_answer")
        prompt = chain_text(field.get("question_text")) or column
        if prompt == column:
            pieces.append(f"{column} [{role}]: {answer}")
        else:
            pieces.append(f"{column} [{role}] {prompt}: {answer}")
    return " || ".join(pieces), len(pieces)


def full_response_chain(row: pd.Series, question_chain: pd.DataFrame) -> tuple[str, int]:
    return response_chain(row, question_chain, "include_in_full_response_chain")


def focused_semantic_chain(row: pd.Series, question_chain: pd.DataFrame) -> tuple[str, int]:
    if "include_in_focused_semantic_chain" not in question_chain.columns:
        return response_chain(row, question_chain, "include_in_full_response_chain")
    focused = question_chain[question_chain["include_in_focused_semantic_chain"].map(truthy)]
    return response_chain(row, focused, "include_in_focused_semantic_chain")


def role_class(value: object) -> str:
    raw = text(value)
    if not raw:
        return "missing_role"
    if ABUSIVE_TERMS.search(raw):
        return "non_cooperative"
    has_trade = bool(TRADE_TERMS.search(raw))
    has_non_trade = bool(NON_TRADE_TERMS.search(raw))
    has_maybe = bool(MAYBE_ROLE_TERMS.search(raw))
    if has_trade:
        return "trade_relevant"
    if has_non_trade:
        return "likely_non_trade"
    if has_maybe or len(raw.split()) <= 3:
        return "ambiguous_role"
    return "unclear_role"


def brand_token_class(value: object) -> str:
    raw = text(value)
    if not raw:
        return "blank"
    if ABUSIVE_TERMS.search(raw):
        return "hostile_or_abusive"
    if INVALID_BRAND_TERMS.fullmatch(raw):
        return "invalid_or_too_generic"
    if BRAND_TERMS.search(raw):
        return "valid_brand_or_variant"
    if TOOL_CATEGORY_TERMS.search(raw):
        return "tool_category_not_brand"
    if len(raw) <= 2:
        return "too_short_unknown"
    if re.fullmatch(r"[A-Za-z ]{3,35}", raw):
        return "unknown_possible_brand"
    return "other_unknown"


def brand_quality(row: pd.Series, brand_cols: list[str]) -> tuple[str, int, str]:
    values = [text(row.get(col)) for col in brand_cols if text(row.get(col))]
    if not values:
        if not brand_cols:
            return "not_applicable_no_brand_list", 0, ""
        return "missing_brand_list", 0, ""
    classes = [brand_token_class(value) for value in values]
    counts = Counter(classes)
    if counts["hostile_or_abusive"]:
        quality = "hostile_brand_answer"
    elif counts["valid_brand_or_variant"] or counts["tool_category_not_brand"]:
        quality = "has_valid_brand_or_tool_category"
    elif counts["unknown_possible_brand"]:
        quality = "unknown_possible_brand_only"
    elif counts["invalid_or_too_generic"] or counts["too_short_unknown"]:
        quality = "weak_or_invalid_brand_list"
    else:
        quality = "unknown_brand_quality"
    details = "; ".join(f"{value} [{brand_token_class(value)}]" for value in values[:12])
    return quality, len(values), details


def repeated_phrase_risk(raw: str) -> bool:
    tokens = re.findall(r"[a-z']+", raw.lower())
    if len(tokens) < 6:
        return False
    for size in (2, 3, 4):
        grams = [" ".join(tokens[index : index + size]) for index in range(len(tokens) - size + 1)]
        counts = Counter(grams)
        if counts and max(counts.values()) >= 3:
            return True
    return False


TECHNICAL_TEXT_FIELD_TERMS = re.compile(
    r"(^rd_|token|uuid|rid|session|url|useragent|browser|mobile|device|ipaddress|dcua|camp|source|supname|intcode)",
    re.I,
)
CHAIN_EXCLUDED_ROLES = {
    "respondent_identifier",
    "timing_field",
    "fielding_timestamp",
    "ip_or_device_field",
    "supplier_or_source_field",
    "demographic_field",
    "review_helper",
    "technical_or_hidden_field",
}


def open_end_columns_from_summary(summary: dict) -> list[str]:
    columns: list[str] = []
    for profile in summary.get("discovery_profiles", {}).values():
        columns.extend(str(item) for item in profile.get("open_end_columns", []) if str(item).strip())
    return list(dict.fromkeys(columns))


def useful_text_values(source: pd.DataFrame, col: str) -> pd.Series:
    series = source[col]
    values = series.dropna().astype(str).str.strip()
    return values[values.ne("")]


def detect_narrative_col(source: pd.DataFrame, summary: dict | None = None) -> str | None:
    preferred = ["outro", "qc5", "open_end", "openend", "comment", "comments"]
    for col in preferred:
        if col in source.columns:
            return col

    summary = summary or {}
    open_end_cols = [col for col in open_end_columns_from_summary(summary) if col in source.columns and not TECHNICAL_TEXT_FIELD_TERMS.search(col)]
    if open_end_cols:
        ranked: list[tuple[int, float, str]] = []
        for col in open_end_cols:
            values = useful_text_values(source, col)
            if values.empty:
                continue
            ranked.append((len(values), float(values.str.len().mean()), col))
        if ranked:
            ranked.sort(reverse=True)
            return ranked[0][2]

    candidates: list[tuple[float, int, str]] = []
    for col in source.columns:
        if TECHNICAL_TEXT_FIELD_TERMS.search(str(col)):
            continue
        series = source[col]
        if not (pd.api.types.is_object_dtype(series) or pd.api.types.is_string_dtype(series)):
            continue
        values = useful_text_values(source, str(col))
        if len(values) < max(20, len(source) // 10):
            continue
        avg_len = float(values.str.len().mean())
        if avg_len >= 20:
            candidates.append((avg_len, len(values), str(col)))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][2]


def narrative_quality(value: object, topic_re: re.Pattern[str] | None = None) -> str:
    raw = text(value)
    if not raw:
        return "blank"
    lowered = raw.lower()
    words = re.findall(r"[a-z0-9']+", lowered)
    unique_words = set(words)
    if ABUSIVE_TERMS.search(raw) or NON_COOPERATIVE_NARRATIVE_TERMS.fullmatch(lowered):
        return "non_cooperative"
    if repeated_phrase_risk(raw):
        return "nonsensical_or_repetitive"
    has_topic = bool(topic_re.search(raw)) if topic_re else False
    has_substantive_factor = bool(SUBSTANTIVE_FACTOR_TERMS.search(raw))
    if GENERIC_SURVEY_FEEDBACK_TERMS.search(raw) and not has_topic and not has_substantive_factor:
        return "generic_survey_feedback"
    if has_topic:
        if len(words) <= 2 or len(unique_words) <= 2:
            return "low_information"
        return "topic_relevant"
    if has_substantive_factor:
        if len(words) <= 2 or len(unique_words) <= 2:
            return "low_information"
        return "substantive_narrative"
    if len(words) <= 3 or len(unique_words) <= 2:
        return "low_information"
    return "unclear_product_answer"


def duplicate_cluster_stats(source: pd.DataFrame) -> dict[str, dict[str, object]]:
    if "ipAddress" not in source.columns:
        return {}
    key_cols = [col for col in ["uuid", "record", "RID", "session", "SUPNAME", "source"] if col in source.columns]
    stats: dict[str, dict[str, object]] = {}
    for value, group in source[source["ipAddress"].map(lambda item: bool(text(item)))].groupby("ipAddress", dropna=False):
        ip_value = text(value)
        row: dict[str, object] = {"rows": int(len(group))}
        for col in key_cols:
            nonempty = group[col].dropna().astype(str).str.strip()
            nonempty = nonempty[nonempty.ne("")]
            row[f"{col}_n"] = int(nonempty.nunique())
        session_n = int(row.get("session_n", 0))
        supplier_n = int(row.get("SUPNAME_n", 0))
        source_n = int(row.get("source_n", 0))
        if row["rows"] <= 1:
            row["cluster_type"] = "single"
        elif session_n <= 1 and supplier_n <= 1 and source_n <= 1:
            row["cluster_type"] = "shared_response_chain"
        else:
            row["cluster_type"] = "independent_duplicate_cluster"
        stats[ip_value] = row
    return stats


def suggested_action(role: str, brand: str, narrative: str, qtime: float | None, duplicate_type: str) -> tuple[str, str]:
    risks: list[str] = []
    if role in {"likely_non_trade", "non_cooperative"}:
        risks.append("role_fit_risk")
    if role in {"ambiguous_role", "unclear_role"}:
        risks.append("role_calibration_needed")
    if brand in {"hostile_brand_answer", "weak_or_invalid_brand_list", "unknown_brand_quality"}:
        risks.append("brand_answer_risk")
    if narrative in {"non_cooperative", "nonsensical_or_repetitive"}:
        risks.append("narrative_discard_risk")
    if narrative in {"generic_survey_feedback", "low_information", "unclear_product_answer"}:
        risks.append("narrative_quality_risk")
    if qtime is not None and qtime < 240:
        risks.append("speed_risk")
    if duplicate_type == "independent_duplicate_cluster":
        risks.append("duplicate_ip_risk")

    role_ok = role in {"trade_relevant", "not_applicable_no_role_field"}
    brand_ok = brand in {
        "has_valid_brand_or_tool_category",
        "unknown_possible_brand_only",
        "not_applicable_no_brand_list",
    }
    narrative_ok = narrative in {"topic_relevant", "substantive_narrative", "not_applicable_no_narrative_field"}
    if role_ok and brand_ok and narrative_ok and "speed_risk" not in risks and "duplicate_ip_risk" not in risks:
        return "keep_no_issue_from_independent_audit", "none"
    if "narrative_discard_risk" in risks:
        return "review_for_possible_discard", "; ".join(risks)
    if "role_fit_risk" in risks and ("duplicate_ip_risk" in risks or "brand_answer_risk" in risks or "speed_risk" in risks):
        return "review_for_possible_discard", "; ".join(risks)
    if "narrative_quality_risk" in risks and "speed_risk" in risks:
        return "review_for_possible_discard", "; ".join(risks)
    if risks:
        return "review_or_pm_calibration", "; ".join(risks)
    return "keep_no_issue_from_independent_audit", "none"


def write_markdown(run_dir: Path, audit: pd.DataFrame, judgments: pd.DataFrame) -> None:
    reviewed = int(audit["autosurvey_reviewed"].sum())
    candidates = audit[audit["independent_suggested_action"].ne("keep_no_issue_from_independent_audit")]
    missed = candidates[~candidates["autosurvey_reviewed"]]
    safe_reviewed = audit[audit["autosurvey_reviewed"] & audit["independent_suggested_action"].eq("keep_no_issue_from_independent_audit")]
    possible_missed = audit[audit["independent_suggested_action"].eq("review_for_possible_discard") & ~audit["autosurvey_agent_discard"]]

    lines = [
        "# Independent full-response audit",
        "",
        "## Scope",
        "",
        f"Rows audited: {len(audit)}.",
        "This audit starts from the raw workbook, not from the autosurvey review queue.",
        "It stitches the ordered question chain and each respondent's full response chain before classifying the row.",
        "It classifies every response for role fit, brand-list quality, duplicate IP, timing, full-chain answer context, and whether autosurvey reviewed the row.",
        "",
        "## Independent classifications",
        "",
    ]
    for label, column in [
        ("Role class", "role_class"),
        ("Brand answer quality", "brand_quality"),
        ("Narrative quality", "narrative_quality"),
        ("Suggested action", "independent_suggested_action"),
    ]:
        lines.append(f"### {label}")
        for value, count in audit[column].value_counts().items():
            lines.append(f"- {value}: {int(count)}")
        lines.append("")

    lines.extend(
        [
            "## Comparison to autosurvey",
            "",
            f"- Autosurvey reviewed rows: {reviewed}.",
            f"- Independent audit review candidates: {len(candidates)}.",
            f"- Independent review candidates not reviewed by autosurvey: {len(missed)}.",
            f"- Autosurvey-reviewed rows that this audit would keep without review: {len(safe_reviewed)}.",
            f"- Independent possible-discard rows not left in the autosurvey discard set: {len(possible_missed)}.",
            "",
            "## Missed review candidates by reason",
            "",
        ]
    )
    if missed.empty:
        lines.append("No missed independent review candidates were found.")
    else:
        for reason, count in missed["independent_risk_factors"].value_counts().head(20).items():
            lines.append(f"- {reason}: {int(count)}")

    lines.extend(["", "## Possible missed discard or escalation rows", ""])
    if possible_missed.empty:
        lines.append("No possible missed discard rows were found by the independent audit.")
    else:
        joined = possible_missed.merge(
            judgments[["respondent_key", "agent_final_decision", "review_theme"]] if not judgments.empty else pd.DataFrame(columns=["respondent_key", "agent_final_decision", "review_theme"]),
            on="respondent_key",
            how="left",
        )
        for _, row in joined.head(40).iterrows():
            lines.append(
                f"- {row['respondent_key']}: {row['independent_risk_factors']}. "
                f"Role: {row['qcoe1']}. Brand: {row['brand_answer_details']}. "
                f"Narrative: {row['narrative_text']}. "
                f"Reviewed: {row['autosurvey_reviewed']}. Agent decision: {text(row.get('agent_final_decision'))}."
            )

    lines.extend(
        [
            "",
            "## Audit conclusion",
            "",
            "The workflow is not perfect on new datasets. The agent review layer can correct many first-pass errors, but the run still needs an independent full-row audit before final delivery.",
            "The audit checks whether the scorer missed rows because the triggered evidence table did not include the full source row.",
            "When the audit finds a possible missed discard or a large false-positive group, update the agent judgment artifacts and feed the finding into the next-pass signal inventory.",
            "",
        ]
    )
    (run_dir / "independent_full_response_audit.md").write_text("\n".join(lines), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--sheet", default="A1")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_dir = args.run_dir.expanduser().resolve()
    summary = run_summary(run_dir)
    workbook = source_workbook(run_dir)
    source = pd.read_excel(workbook, sheet_name=args.sheet)
    question_chain = load_question_chain_map(run_dir, source, workbook.name, args.sheet, summary)
    if not (run_dir / "question_chain_map.csv").exists():
        question_chain.to_csv(run_dir / "question_chain_map.csv", index=False)
    respondent = read_csv(run_dir / "respondent_review_table.csv")
    judgments = read_csv(run_dir / "agent_review_judgment_table.csv")

    key_col = "uuid" if "uuid" in source.columns else "record"
    role_candidates = question_chain.loc[
        question_chain.get("field_role", pd.Series(dtype=str)).astype(str).eq("job_role_screener"),
        "source_column",
    ].astype(str).tolist() if "field_role" in question_chain and "source_column" in question_chain else []
    role_col = next((col for col in role_candidates if col in source.columns), None)
    brand_cols = [col for col in source.columns if re.match(r"qcoe2r\d+$", str(col))]
    narrative_col = detect_narrative_col(source, summary)
    topic_re = topic_pattern(summary)
    duplicate_stats = duplicate_cluster_stats(source)
    agent_reviewed_keys = set(judgments.get("respondent_key", pd.Series(dtype=str)).astype(str))
    reviewed_keys: set[str] = set()
    if not respondent.empty and "second_pass_decision" in respondent:
        queued = respondent[respondent["second_pass_decision"].astype(str).ne("keep_no_issue")]
        reviewed_keys.update(queued["respondent_key"].astype(str))
    discard_keys = set(judgments.loc[judgments.get("agent_final_decision", pd.Series(dtype=str)).astype(str).eq("discard"), "respondent_key"].astype(str)) if not judgments.empty else set()

    rows: list[dict[str, object]] = []
    for _, row in source.iterrows():
        key = text(row.get(key_col)) or str(row.name)
        role = role_class(row.get(role_col, "")) if role_col else "not_applicable_no_role_field"
        brand, brand_count, brand_details = brand_quality(row, brand_cols)
        narrative = narrative_quality(row.get(narrative_col), topic_re) if narrative_col else "not_applicable_no_narrative_field"
        qtime_value = pd.to_numeric(pd.Series([row.get("qtime")]), errors="coerce").iloc[0] if "qtime" in source.columns else None
        qtime = None if pd.isna(qtime_value) else float(qtime_value)
        cluster = duplicate_stats.get(text(row.get("ipAddress")), {})
        duplicate_count = int(cluster.get("rows", 0))
        duplicate_type = text(cluster.get("cluster_type")) if duplicate_count > 1 else "single"
        action, risks = suggested_action(role, brand, narrative, qtime, duplicate_type)
        response_chain, response_chain_fields = full_response_chain(row, question_chain)
        semantic_chain, semantic_chain_fields = focused_semantic_chain(row, question_chain)
        rows.append(
            {
                "respondent_key": key,
                "record": row.get("record"),
                "supplier": text(row.get("SUPNAME")) or text(row.get("source")) or "missing",
                "ipAddress": text(row.get("ipAddress")),
                "duplicate_ip_count": duplicate_count,
                "duplicate_cluster_type": duplicate_type,
                "duplicate_session_count": int(cluster.get("session_n", 0)) if cluster else 0,
                "duplicate_supplier_count": int(cluster.get("SUPNAME_n", 0)) if cluster else 0,
                "duplicate_rid_count": int(cluster.get("RID_n", 0)) if cluster else 0,
                "qtime": qtime,
                "qcoe1": text(row.get(role_col)) if role_col else "",
                "role_class": role,
                "brand_quality": brand,
                "brand_answer_count": brand_count,
                "brand_answer_details": brand_details,
                "narrative_column": narrative_col or "",
                "narrative_quality": narrative,
                "narrative_text": text(row.get(narrative_col))[:240] if narrative_col else "",
                "response_chain_field_count": response_chain_fields,
                "full_response_chain": response_chain,
                "semantic_review_chain_field_count": semantic_chain_fields,
                "semantic_review_chain": semantic_chain,
                "independent_risk_factors": risks,
                "independent_suggested_action": action,
                "autosurvey_reviewed": key in reviewed_keys,
                "agent_reviewed": key in agent_reviewed_keys,
                "autosurvey_agent_discard": key in discard_keys,
            }
        )

    audit = pd.DataFrame(rows)
    if not respondent.empty:
        audit = audit.merge(
            respondent[["respondent_key", "computed_action", "computed_score", "second_pass_decision", "criteria_triggered", "observed_evidence"]],
            on="respondent_key",
            how="left",
        )
    audit.to_csv(run_dir / "independent_full_response_audit.csv", index=False)
    write_markdown(run_dir, audit, judgments)

    print(run_dir / "independent_full_response_audit.csv")
    print(run_dir / "independent_full_response_audit.md")


if __name__ == "__main__":
    main()
