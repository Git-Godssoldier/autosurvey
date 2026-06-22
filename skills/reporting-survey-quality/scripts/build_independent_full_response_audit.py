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


def text(value: object, default: str = "") -> str:
    if pd.isna(value):
        return default
    return str(value).strip()


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


def suggested_action(role: str, brand: str, qtime: float | None, duplicate_count: int) -> tuple[str, str]:
    risks: list[str] = []
    if role in {"likely_non_trade", "non_cooperative"}:
        risks.append("role_fit_risk")
    if role in {"ambiguous_role", "unclear_role"}:
        risks.append("role_calibration_needed")
    if brand in {"hostile_brand_answer", "weak_or_invalid_brand_list", "unknown_brand_quality"}:
        risks.append("brand_answer_risk")
    if qtime is not None and qtime < 240:
        risks.append("speed_risk")
    if duplicate_count > 1:
        risks.append("duplicate_ip_risk")

    if role == "trade_relevant" and brand in {"has_valid_brand_or_tool_category", "unknown_possible_brand_only"} and "speed_risk" not in risks and "duplicate_ip_risk" not in risks:
        return "keep_no_issue_from_independent_audit", "none"
    if "role_fit_risk" in risks and ("duplicate_ip_risk" in risks or "brand_answer_risk" in risks or "speed_risk" in risks):
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
        "It classifies every response for role fit, brand-list quality, duplicate IP, timing, and whether autosurvey reviewed the row.",
        "",
        "## Independent classifications",
        "",
    ]
    for label, column in [
        ("Role class", "role_class"),
        ("Brand answer quality", "brand_quality"),
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
    workbook = source_workbook(run_dir)
    source = pd.read_excel(workbook, sheet_name=args.sheet)
    respondent = read_csv(run_dir / "respondent_review_table.csv")
    judgments = read_csv(run_dir / "agent_review_judgment_table.csv")

    key_col = "uuid" if "uuid" in source.columns else "record"
    role_col = "qcoe1" if "qcoe1" in source.columns else None
    brand_cols = [col for col in source.columns if re.match(r"qcoe2r\d+$", str(col))]
    ip_counts = source["ipAddress"].fillna("").astype(str).value_counts().to_dict() if "ipAddress" in source else {}
    reviewed_keys = set(judgments.get("respondent_key", pd.Series(dtype=str)).astype(str))
    discard_keys = set(judgments.loc[judgments.get("agent_final_decision", pd.Series(dtype=str)).astype(str).eq("discard"), "respondent_key"].astype(str)) if not judgments.empty else set()

    rows: list[dict[str, object]] = []
    for _, row in source.iterrows():
        key = text(row.get(key_col)) or str(row.name)
        role = role_class(row.get(role_col, "")) if role_col else "missing_role"
        brand, brand_count, brand_details = brand_quality(row, brand_cols)
        qtime_value = pd.to_numeric(pd.Series([row.get("qtime")]), errors="coerce").iloc[0] if "qtime" in source.columns else None
        qtime = None if pd.isna(qtime_value) else float(qtime_value)
        duplicate_count = int(ip_counts.get(text(row.get("ipAddress")), 0))
        action, risks = suggested_action(role, brand, qtime, duplicate_count)
        rows.append(
            {
                "respondent_key": key,
                "record": row.get("record"),
                "supplier": text(row.get("SUPNAME")) or text(row.get("source")) or "missing",
                "ipAddress": text(row.get("ipAddress")),
                "duplicate_ip_count": duplicate_count,
                "qtime": qtime,
                "qcoe1": text(row.get(role_col)) if role_col else "",
                "role_class": role,
                "brand_quality": brand,
                "brand_answer_count": brand_count,
                "brand_answer_details": brand_details,
                "independent_risk_factors": risks,
                "independent_suggested_action": action,
                "autosurvey_reviewed": key in reviewed_keys,
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
