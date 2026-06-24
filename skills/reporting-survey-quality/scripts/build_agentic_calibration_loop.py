#!/usr/bin/env python3
"""Build frozen-loop calibration artifacts from TFG status-labeled outputs."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import pandas as pd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--annotated-input", type=Path, required=True, help="Directory, zip, or workbook used for methodology development.")
    parser.add_argument("--calibration-dir", type=Path, required=True, help="Directory containing status calibration artifacts.")
    parser.add_argument("--heldout-input", type=Path, help="Blinded workbook or directory that must remain unscored.")
    return parser.parse_args()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def input_files(path: Path) -> list[dict[str, object]]:
    path = path.expanduser().resolve()
    if path.is_file():
        files = [path]
    else:
        files = sorted(child for child in path.rglob("*") if child.suffix.lower() in {".xlsx", ".zip", ".csv"})
    rows: list[dict[str, object]] = []
    for file_path in files:
        if file_path.name.startswith("~$"):
            continue
        rows.append(
            {
                "path": str(file_path),
                "name": file_path.name,
                "bytes": file_path.stat().st_size,
                "sha256": sha256(file_path),
            }
        )
    return rows


def read_csv(path: Path) -> pd.DataFrame:
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def status_totals(summary: pd.DataFrame, blind: pd.DataFrame) -> dict[str, int]:
    if not summary.empty and {"accepted_status_3", "rejected_status_5"} <= set(summary.columns):
        accepted = int(pd.to_numeric(summary["accepted_status_3"], errors="coerce").fillna(0).sum())
        rejected = int(pd.to_numeric(summary["rejected_status_5"], errors="coerce").fillna(0).sum())
        return {"accepted": accepted, "rejected": rejected, "total": accepted + rejected}
    if not blind.empty and "status" in blind.columns:
        status = blind["status"].astype(str).str.replace(r"\.0$", "", regex=True)
        accepted = int(status.eq("3").sum())
        rejected = int(status.eq("5").sum())
        return {"accepted": accepted, "rejected": rejected, "total": accepted + rejected}
    return {"accepted": 0, "rejected": 0, "total": 0}


def chart_label(value: object) -> str:
    raw = str(value).replace("_", " ").replace("-", " ").strip()
    return raw[:1].upper() + raw[1:] if raw else "Unknown"


def specs_from_family_lift(family: pd.DataFrame) -> pd.DataFrame:
    if family.empty:
        return pd.DataFrame()
    df = family.copy()
    for col in ["threshold", "n", "rejected", "accepted", "reject_rate_when_present", "lift_vs_base", "status5_coverage", "status3_false_positive_exposure"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    if "threshold" in df.columns and (df["threshold"] == 2).any():
        df = df[df["threshold"] == 2].copy()
    rows = []
    for _, row in df.sort_values(["lift_vs_base", "n"], ascending=[False, False]).iterrows():
        family_name = str(row.get("family", "unknown"))
        lift = float(row.get("lift_vs_base", 0))
        accepted_exposure = float(row.get("status3_false_positive_exposure", 0))
        if lift >= 1.5 and accepted_exposure < 0.05:
            disposition = "promote_to_review_routing"
        elif lift >= 1.1:
            disposition = "hold_for_agent_review"
        elif accepted_exposure >= 0.10:
            disposition = "guardrail_or_report_only"
        else:
            disposition = "demote_until_more_evidence"
        rows.append(
            {
                "signal_family": family_name,
                "plain_language_signal": chart_label(family_name),
                "support_rows": int(row.get("n", 0)),
                "rejected_rows": int(row.get("rejected", 0)),
                "accepted_counterexamples": int(row.get("accepted", 0)),
                "reject_rate_when_present": round(float(row.get("reject_rate_when_present", 0)), 4),
                "lift_vs_base": round(lift, 3),
                "accepted_exposure": round(accepted_exposure, 4),
                "current_disposition": disposition,
                "falsifiable_test": "The signal should separate rejected rows from similar accepted controls after question-set mapping and full-chain review.",
                "counterexample_attack": "Compare every high-risk row with accepted rows that share the same surface pattern before using it for exclusion.",
                "runtime_instruction": "Use as a natural-language evidence question on blank Decipher exports; do not require status labels.",
            }
        )
    return pd.DataFrame(rows)


def specs_from_rule_evidence(evidence: pd.DataFrame) -> pd.DataFrame:
    if evidence.empty or "rule_id" not in evidence.columns:
        return pd.DataFrame()
    df = evidence.copy()
    for col in ["accepted_hits", "rejected_hits", "support_rows", "reject_rate_when_rule_fires", "dataset_reject_rate"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    grouped_rows = []
    group_cols = ["rule_id", "name", "family", "description", "use_on_unannotated_data", "guardrail", "rulebook_transfer_role"]
    for keys, group in df.groupby(group_cols, dropna=False):
        record = dict(zip(group_cols, keys))
        accepted = int(group["accepted_hits"].sum())
        rejected = int(group["rejected_hits"].sum())
        support = accepted + rejected
        reject_rate = rejected / support if support else 0
        base_numerator = (group["dataset_reject_rate"] * group["support_rows"]).sum()
        base_denominator = group["support_rows"].sum()
        base_rate = float(base_numerator / base_denominator) if base_denominator else 0
        lift = reject_rate / base_rate if base_rate else 0
        accepted_exposure = accepted / max(evidence["accepted_hits"].sum(), 1)
        transfer_role = str(record.get("rulebook_transfer_role", ""))
        if support == 0:
            disposition = "unobserved_runtime_question"
        elif transfer_role == "candidate_discard_signal" and rejected >= 10 and lift >= 1.5:
            disposition = "promote_to_review_routing_with_tier5_audit"
        elif transfer_role in {"review_routing", "agent_semantic_rule"} or lift >= 1.1:
            disposition = "hold_for_agent_review"
        elif accepted > rejected:
            disposition = "guardrail_or_report_only"
        else:
            disposition = "demote_until_more_evidence"
        grouped_rows.append(
            {
                "signal_family": record.get("family", ""),
                "signal_id": record.get("rule_id", ""),
                "plain_language_signal": record.get("name", ""),
                "support_rows": support,
                "rejected_rows": rejected,
                "accepted_counterexamples": accepted,
                "reject_rate_when_present": round(reject_rate, 4),
                "lift_vs_base": round(lift, 3),
                "accepted_exposure": round(accepted_exposure, 4),
                "current_disposition": disposition,
                "falsifiable_test": record.get("description", ""),
                "counterexample_attack": record.get("guardrail", ""),
                "runtime_instruction": record.get("use_on_unannotated_data", ""),
            }
        )
    return pd.DataFrame(grouped_rows).sort_values(
        ["current_disposition", "lift_vs_base", "support_rows"],
        ascending=[True, False, False],
    )


def controls_from_contrast(contrast: pd.DataFrame, limit: int = 50) -> pd.DataFrame:
    if contrast.empty:
        return pd.DataFrame()
    rows = []
    for _, row in contrast.head(limit).iterrows():
        outcome = str(row.get("contrast_outcome", ""))
        if outcome == "status3_false_exclude_risk":
            control_role = "accepted_control_for_false_exclude"
            learning = "Find the human evidence that protected this accepted row before promoting the signal."
        elif outcome == "status5_blind_miss":
            control_role = "rejected_control_for_blind_miss"
            learning = "Find the semantic signal the blind pass missed and compare it to similar accepted rows."
        elif outcome == "status5_blind_exclude_match":
            control_role = "rejected_support_for_tier5"
            learning = "Audit the full response chain and similar accepted controls before using this as exclusion evidence."
        else:
            control_role = "review_control"
            learning = "Use this row to understand where review routing differs from exclusion."
        rows.append(
            {
                "workbook": row.get("workbook", ""),
                "respondent_key": row.get("respondent_key", ""),
                "source_row_index": row.get("source_row_index", ""),
                "contrast_outcome": outcome,
                "control_role": control_role,
                "blind_tier": row.get("blind_tier", ""),
                "blind_tier_name": row.get("blind_tier_name", ""),
                "family_reasons": row.get("family_reasons", ""),
                "protective_evidence": row.get("protective_evidence", ""),
                "learning_task": learning,
            }
        )
    return pd.DataFrame(rows)


def controls_from_rule_evidence(evidence: pd.DataFrame, limit: int = 120) -> pd.DataFrame:
    if evidence.empty:
        return pd.DataFrame()
    rows: list[dict[str, object]] = []
    by_role: dict[str, int] = defaultdict(int)
    for _, rule in evidence.iterrows():
        rule_id = rule.get("rule_id", "")
        name = rule.get("name", "")
        family = rule.get("family", "")
        for column, role, task in [
            (
                "rejected_examples_json",
                "rejected_control",
                "Compare this rejected example with similar accepted rows before promoting the signal.",
            ),
            (
                "accepted_examples_json",
                "accepted_guardrail",
                "Use this accepted example to attack the signal and protect legitimate respondents.",
            ),
        ]:
            try:
                examples = json.loads(rule.get(column, "[]") or "[]")
            except (TypeError, json.JSONDecodeError):
                examples = []
            for example in examples[:2]:
                key = f"{role}:{rule_id}"
                if by_role[key] >= 4:
                    continue
                rows.append(
                    {
                        "rule_id": rule_id,
                        "signal_name": name,
                        "family": family,
                        "control_role": role,
                        "workbook": example.get("dataset", ""),
                        "respondent_key": example.get("respondent_key", ""),
                        "source_row_number": example.get("source_row_number", ""),
                        "evidence": example.get("evidence", ""),
                        "chain_readout_excerpt": example.get("open_end_excerpt", ""),
                        "learning_task": task,
                    }
                )
                by_role[key] += 1
                if len(rows) >= limit:
                    return pd.DataFrame(rows)
    return pd.DataFrame(rows)


def markdown_report(
    totals: dict[str, int],
    manifest_rows: list[dict[str, object]],
    heldout_rows: list[dict[str, object]],
    specs: pd.DataFrame,
    contrast_summary: pd.DataFrame,
) -> str:
    rejected = totals["rejected"]
    accepted = totals["accepted"]
    total = totals["total"]
    reject_rate = rejected / total if total else 0
    promoted = int(specs["current_disposition"].astype(str).str.startswith("promote_to_review_routing").sum()) if not specs.empty else 0
    held = int(specs["current_disposition"].eq("hold_for_agent_review").sum()) if not specs.empty else 0
    guardrails = int(specs["current_disposition"].eq("guardrail_or_report_only").sum()) if not specs.empty else 0
    unobserved = int(specs["current_disposition"].eq("unobserved_runtime_question").sum()) if not specs.empty else 0
    lines = [
        "# Agentic calibration loop execution report",
        "",
        "## Frozen inputs",
        "",
        f"We froze {len(manifest_rows)} annotated input files for methodology development.",
        f"The labeled corpus contains {total:,} respondents: {accepted:,} accepted rows and {rejected:,} rejected rows. The rejected rate is {reject_rate:.1%}.",
        "",
    ]
    if heldout_rows:
        lines.extend(
            [
                "## Held-out blinded data",
                "",
                f"We identified {len(heldout_rows)} held-out file(s). These files are frozen as blinded validation inputs and were not scored in this calibration loop.",
                "",
            ]
        )
    lines.extend(
        [
            "## Loop status",
            "",
            "- Inputs frozen and hashed.",
            "- Status labels are treated as observed client outcomes, not proof of fraud.",
            "- Blind and label-aware artifacts are kept in the calibration folder.",
            "- Transferable signal specifications were written as natural-language runtime questions.",
            "- The blinded dataset remains untouched until the specifications are frozen.",
            "",
            "## Signal promotion summary",
            "",
            f"- Promoted to review routing: {promoted}",
            f"- Held for agent review: {held}",
            f"- Guardrail or report only: {guardrails}",
            f"- Unobserved runtime questions retained for blank-set review: {unobserved}",
            "",
        ]
    )
    if not contrast_summary.empty:
        lines.extend(["## Label-aware contrast outcomes", ""])
        for _, row in contrast_summary.iterrows():
            lines.append(f"- {chart_label(row.get('contrast_outcome'))}: {int(row.get('rows', 0)):,} rows")
        lines.append("")
    if not specs.empty:
        lines.extend(["## Transferable signal specifications", ""])
        for _, row in specs.iterrows():
            lines.append(
                f"- {chart_label(row['signal_family'])}: {row['current_disposition']}. "
                f"Support {int(row['support_rows']):,}; rejected {int(row['rejected_rows']):,}; "
                f"accepted counterexamples {int(row['accepted_counterexamples']):,}; lift {row['lift_vs_base']}."
            )
        lines.append("")
    lines.extend(
        [
            "## Next loop requirement",
            "",
            "Continue from residual errors. Read the control-match table and semantic packets, update the signal bank, and do not score the blinded dataset until no stable new signal remains unresolved.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    calibration_dir = args.calibration_dir.expanduser().resolve()
    calibration_dir.mkdir(parents=True, exist_ok=True)

    manifest_rows = input_files(args.annotated_input)
    heldout_rows = input_files(args.heldout_input) if args.heldout_input else []
    (calibration_dir / "frozen_input_manifest.json").write_text(
        json.dumps({"annotated_inputs": manifest_rows, "heldout_inputs": heldout_rows}, indent=2),
        encoding="utf-8",
    )
    pd.DataFrame(manifest_rows).to_csv(calibration_dir / "frozen_annotated_input_manifest.csv", index=False)
    if heldout_rows:
        pd.DataFrame(heldout_rows).to_csv(calibration_dir / "frozen_heldout_input_manifest.csv", index=False)

    summary = read_csv(calibration_dir / "status_dataset_summary.csv")
    if summary.empty:
        summary = read_csv(calibration_dir / "workbook_status_summary.csv")
    blind = read_csv(calibration_dir / "blind_authenticity_review_table.csv")
    family = read_csv(calibration_dir / "authenticity_signal_family_lift.csv")
    rule_evidence = read_csv(calibration_dir / "tfg_discard_rule_evidence.csv")
    contrast = read_csv(calibration_dir / "label_aware_contrast_table.csv")
    contrast_summary = read_csv(calibration_dir / "contrast_outcome_summary.csv")

    totals = status_totals(summary, blind)
    specs = specs_from_family_lift(family)
    if specs.empty:
        specs = specs_from_rule_evidence(rule_evidence)
    specs.to_csv(calibration_dir / "transferable_signal_specifications.csv", index=False)

    controls = controls_from_contrast(contrast)
    if controls.empty:
        controls = controls_from_rule_evidence(rule_evidence)
    controls.to_csv(calibration_dir / "control_match_backlog.csv", index=False)

    report = markdown_report(totals, manifest_rows, heldout_rows, specs, contrast_summary)
    (calibration_dir / "agentic_calibration_loop_report.md").write_text(report, encoding="utf-8")
    print(calibration_dir / "agentic_calibration_loop_report.md")
    print(calibration_dir / "transferable_signal_specifications.csv")
    print(calibration_dir / "control_match_backlog.csv")


if __name__ == "__main__":
    main()
