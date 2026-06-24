#!/usr/bin/env python3
"""Derive authenticity signals from TFG status-labeled workbooks."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from io import BytesIO
from pathlib import Path
from zipfile import ZipFile

import pandas as pd


ACCEPTED_STATUS = "3"
REJECTED_STATUS = "5"
TEXT_EXCLUDE = re.compile(
    r"token|uuid|record|rid|date|time|zip|state|city|dma|region|country|province|email|phone|ip|url",
    re.I,
)
OPEN_TEXT_HINT = re.compile(r"oe$|open|outro|qcoe|other|specify|explain|why|comment|_pasted$", re.I)
HELPER_HINT = re.compile(r"TERMFLAGS|SCRUTINYFLAGS|CLIENTFLAGS|redem_excluded|RD_Search|RD_Review", re.I)


def text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def normalized_status(value: object) -> str:
    raw = text(value)
    if raw.endswith(".0"):
        raw = raw[:-2]
    return raw


def norm_answer(value: object) -> str:
    raw = re.sub(r"\s+", " ", text(value).lower()).strip()
    return raw


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="Annotated .xlsx, .zip, or directory.")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--sheet", default="A1")
    parser.add_argument("--id-column", default="uuid")
    parser.add_argument("--min-duplicate-length", type=int, default=16)
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


def candidate_text_columns(df: pd.DataFrame) -> list[str]:
    cols: list[str] = []
    for col in df.columns:
        name = text(col)
        if not name or TEXT_EXCLUDE.search(name):
            continue
        series = df[col].dropna().astype(str).str.strip()
        if series.empty:
            continue
        avg_len = series.str.len().mean()
        long_share = (series.str.len() >= 12).mean()
        if OPEN_TEXT_HINT.search(name) or avg_len >= 18 or long_share >= 0.2:
            cols.append(name)
    return cols


def duplicate_maps(df: pd.DataFrame, text_cols: list[str], min_len: int) -> dict[str, dict[str, int]]:
    maps: dict[str, dict[str, int]] = {}
    for col in text_cols:
        counts = Counter(
            value
            for value in df[col].map(norm_answer)
            if len(value) >= min_len and value not in {"none", "nothing", "n/a", "na", "no"}
        )
        maps[col] = {value: count for value, count in counts.items() if count >= 2}
    return maps


def matrix_groups(df: pd.DataFrame) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = defaultdict(list)
    for col in df.columns:
        name = text(col)
        match = re.match(r"(.+?r\d+)r\d+$", name)
        if match:
            groups[match.group(1)].append(name)
            continue
        match = re.match(r"(.+?)[_]?r\d+$", name)
        if match:
            groups[match.group(1)].append(name)
    return {group: cols for group, cols in groups.items() if len(cols) >= 8}


def row_signals(row: pd.Series, text_cols: list[str], duplicates: dict[str, dict[str, int]], matrix_flags: dict[int, list[str]]) -> list[str]:
    signals: list[str] = []

    qtime = pd.to_numeric(row.get("qtime"), errors="coerce") if "qtime" in row.index else pd.NA
    if pd.notna(qtime):
        if qtime < 240:
            signals.append("qtime_under_4_minutes")
        elif qtime < 300:
            signals.append("qtime_4_to_5_minutes")
        elif qtime < 600:
            signals.append("qtime_5_to_10_minutes")

    for col in row.index:
        name = text(col)
        if not HELPER_HINT.search(name):
            continue
        value = text(row.get(col))
        if not value or value in {"0", "0.0", "low", "English"}:
            continue
        if "RD_Review" in name:
            signals.append("rd_review_nonzero")
        elif "RD_Search" in name:
            signals.append(f"{name.lower()}_{value.lower()[:24]}")
        else:
            signals.append(f"{name.lower()}_nonzero")

    duplicate_hit = False
    very_short_hit = False
    generic_hit = False
    polished_hit = False
    long_low_specificity_hit = False
    pasted_hit = False
    for col in text_cols:
        value = text(row.get(col))
        normalized = norm_answer(value)
        if not value:
            continue
        if col.lower().endswith("_pasted") and text(row.get(col)) not in {"0", "0.0"}:
            pasted_hit = True
        if normalized in duplicates.get(col, {}):
            duplicate_hit = True
        words = re.findall(r"[a-zA-Z']+", value)
        if 0 < len(words) <= 2 and col.lower().endswith(("oe", "outro")):
            very_short_hit = True
        if normalized in {"none", "nothing", "n/a", "na", "no", "good", "ok", "idk", "dont know", "don't know"}:
            generic_hit = True
        if "—" in value or re.search(r"\b(as an ai|cannot answer|comprehensive|seamless|valuable insight)\b", value, re.I):
            polished_hit = True
        if len(words) >= 45:
            unique_ratio = len(set(w.lower() for w in words)) / max(len(words), 1)
            if unique_ratio < 0.55:
                long_low_specificity_hit = True

    if duplicate_hit:
        signals.append("duplicate_open_end_text")
    if very_short_hit:
        signals.append("very_short_required_open_end")
    if generic_hit:
        signals.append("generic_placeholder_open_end")
    if polished_hit:
        signals.append("ai_or_overpolished_text_marker")
    if long_low_specificity_hit:
        signals.append("long_low_specificity_text")
    if pasted_hit:
        signals.append("pasted_text_flag")

    for flag in matrix_flags.get(int(row.name), []):
        signals.append(flag)

    return sorted(set(signals))


def derive_for_workbook(entry_name: str, data: bytes, args: argparse.Namespace) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]]:
    df = read_workbook(entry_name, data, args.sheet)
    df.columns = [text(col) for col in df.columns]
    if "status" not in df.columns:
        return [], [], {
            "dataset": entry_name,
            "rows": len(df),
            "has_status": False,
            "note": "No status column. Treat as blinded or unlabeled test data.",
        }

    df["__status"] = df["status"].map(normalized_status)
    labeled = df[df["__status"].isin({ACCEPTED_STATUS, REJECTED_STATUS})].copy()
    if labeled.empty:
        return [], [], {"dataset": entry_name, "rows": len(df), "has_status": True, "labeled_rows": 0}

    text_cols = candidate_text_columns(labeled)
    duplicates = duplicate_maps(labeled, text_cols, args.min_duplicate_length)
    matrix_flags: dict[int, list[str]] = defaultdict(list)
    for group, cols in matrix_groups(labeled).items():
        numeric = labeled[cols].apply(pd.to_numeric, errors="coerce")
        nonempty = numeric.notna().sum(axis=1)
        same_share = numeric.apply(lambda row: row.value_counts(dropna=True).max() / row.count() if row.count() else 0, axis=1)
        for idx in labeled.index[(nonempty >= 8) & (same_share >= 0.9)]:
            matrix_flags[int(idx)].append("matrix_near_straightline")

    respondent_rows = []
    signal_counts: dict[str, Counter[str]] = defaultdict(Counter)
    id_col = args.id_column if args.id_column in labeled.columns else next(
        (col for col in ["uuid", "record", "RID"] if col in labeled.columns),
        "",
    )
    for idx, row in labeled.iterrows():
        status = row["__status"]
        signals = row_signals(row, text_cols, duplicates, matrix_flags)
        key = text(row.get(id_col)) if id_col else str(idx + 2)
        respondent_rows.append(
            {
                "dataset": entry_name,
                "source_row_number": int(idx) + 2,
                "respondent_key": key,
                "status": status,
                "tfg_decision": "accepted" if status == ACCEPTED_STATUS else "rejected",
                "signal_count": len(signals),
                "signals": "; ".join(signals),
            }
        )
        for signal in signals or ["no_detected_script_signal"]:
            signal_counts[signal][status] += 1

    accepted = int((labeled["__status"] == ACCEPTED_STATUS).sum())
    rejected = int((labeled["__status"] == REJECTED_STATUS).sum())
    base_rate = rejected / max(accepted + rejected, 1)
    signal_rows = []
    for signal, counts in signal_counts.items():
        support = counts[ACCEPTED_STATUS] + counts[REJECTED_STATUS]
        rejected_with_signal = counts[REJECTED_STATUS]
        accepted_with_signal = counts[ACCEPTED_STATUS]
        reject_rate = rejected_with_signal / support if support else 0
        signal_rows.append(
            {
                "dataset": entry_name,
                "signal": signal,
                "accepted_rows": accepted_with_signal,
                "rejected_rows": rejected_with_signal,
                "support_rows": support,
                "reject_rate_when_signal_present": round(reject_rate, 4),
                "dataset_reject_rate": round(base_rate, 4),
                "lift_vs_dataset_reject_rate": round(reject_rate / base_rate, 3) if base_rate else 0,
                "signal_role": classify_signal(reject_rate, base_rate, support),
            }
        )

    summary = {
        "dataset": entry_name,
        "rows": len(df),
        "has_status": True,
        "labeled_rows": len(labeled),
        "accepted_status_3": accepted,
        "rejected_status_5": rejected,
        "reject_rate": round(base_rate, 4),
        "text_columns_profiled": len(text_cols),
        "matrix_groups_profiled": len(matrix_groups(labeled)),
        "id_column": id_col,
    }
    return respondent_rows, signal_rows, summary


def classify_signal(reject_rate: float, base_rate: float, support: int) -> str:
    if support < 10:
        return "needs_more_examples"
    if reject_rate >= max(0.6, base_rate * 1.75):
        return "candidate_rejection_signal"
    if reject_rate <= min(0.2, base_rate * 0.55):
        return "accepted_row_guardrail"
    return "context_signal"


def markdown(summaries: list[dict[str, object]], signal_df: pd.DataFrame) -> str:
    labeled = [row for row in summaries if row.get("has_status") and row.get("labeled_rows")]
    accepted = sum(int(row.get("accepted_status_3", 0)) for row in labeled)
    rejected = sum(int(row.get("rejected_status_5", 0)) for row in labeled)
    total = accepted + rejected
    lines = [
        "# TFG status signal derivation",
        "",
        "This calibration pass treats TFG status labels as observed client decisions for training client-rejection signals.",
        "`status = 3` means TFG accepted the respondent.",
        "`status = 5` means TFG rejected the respondent for quality or authenticity concerns.",
        "A status label is not proof of fraud. The agent must still separate client rejection probability from fabrication or authenticity risk.",
        "",
        f"Annotated datasets: {len(labeled)}",
        f"Labeled respondents: {total}",
        f"Accepted status 3: {accepted}",
        f"Rejected status 5: {rejected}",
        f"Overall rejected rate: {(rejected / total * 100):.1f}%" if total else "Overall rejected rate: n/a",
        "",
        "## Dataset rejection rates",
        "",
    ]
    for row in labeled:
        lines.append(
            f"- {row['dataset']}: {row['rejected_status_5']} rejected and "
            f"{row['accepted_status_3']} accepted ({row['reject_rate'] * 100:.1f}% rejected)."
        )
    unlabeled = [row for row in summaries if not row.get("has_status")]
    if unlabeled:
        lines.extend(["", "## Blinded or unlabeled files", ""])
        for row in unlabeled:
            lines.append(f"- {row['dataset']}: {row['rows']} rows and no status column.")

    lines.extend(["", "## Strongest candidate rejection signals", ""])
    top = signal_df[signal_df["signal_role"].eq("candidate_rejection_signal")].sort_values(
        ["lift_vs_dataset_reject_rate", "support_rows"], ascending=[False, False]
    )
    if top.empty:
        lines.append("No high-lift script-staged rejection signals were found. Agent review should inspect the respondent signal map directly.")
    else:
        for _, row in top.head(30).iterrows():
            lines.append(
                f"- {row['dataset']} | {row['signal']}: {row['rejected_rows']} rejected, "
                f"{row['accepted_rows']} accepted, {row['reject_rate_when_signal_present'] * 100:.1f}% rejected, "
                f"{row['lift_vs_dataset_reject_rate']}x dataset rate."
            )

    lines.extend(["", "## Strongest accepted-row guardrails", ""])
    guards = signal_df[signal_df["signal_role"].eq("accepted_row_guardrail")].sort_values(
        ["support_rows", "lift_vs_dataset_reject_rate"], ascending=[False, True]
    )
    if guards.empty:
        lines.append("No accepted-row guardrails were staged by script. The agent should derive guardrails from accepted response chains.")
    else:
        for _, row in guards.head(30).iterrows():
            lines.append(
                f"- {row['dataset']} | {row['signal']}: {row['accepted_rows']} accepted, "
                f"{row['rejected_rows']} rejected, {row['reject_rate_when_signal_present'] * 100:.1f}% rejected."
            )

    lines.extend(
        [
            "",
            "## Analyst requirement",
            "",
            "This file stages statistical evidence. It is not the final interpretation.",
            "The next pass must read all `status = 5` rows to derive fabricated-response signals and all `status = 3` rows to derive stronger false-positive guardrails.",
            "Final signals must be written in plain language with examples, counterexamples, and source citations.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    all_respondents: list[dict[str, object]] = []
    all_signals: list[dict[str, object]] = []
    summaries: list[dict[str, object]] = []

    for entry_name, data in workbook_entries(args.input):
        respondent_rows, signal_rows, summary = derive_for_workbook(entry_name, data, args)
        summaries.append(summary)
        all_respondents.extend(respondent_rows)
        all_signals.extend(signal_rows)

    respondent_df = pd.DataFrame(all_respondents)
    signal_df = pd.DataFrame(all_signals)
    summary_df = pd.DataFrame(summaries)

    respondent_df.to_csv(args.output_dir / "status_respondent_signal_map.csv", index=False)
    signal_df.to_csv(args.output_dir / "status_signal_derivation.csv", index=False)
    summary_df.to_csv(args.output_dir / "status_dataset_summary.csv", index=False)
    (args.output_dir / "status_signal_derivation_summary.json").write_text(
        json.dumps(summaries, indent=2),
        encoding="utf-8",
    )
    (args.output_dir / "status_signal_derivation.md").write_text(markdown(summaries, signal_df), encoding="utf-8")
    print(args.output_dir / "status_signal_derivation.md")


if __name__ == "__main__":
    main()
