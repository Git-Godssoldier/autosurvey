#!/usr/bin/env python3
"""Validate Stage 2 agent judgment JSON files."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path


BASE_REQUIRED_FIELDS = {
    "respondent_id",
    "agent_score",
    "agent_judgment",
    "agent_justification",
}

SIGNAL_REQUIRED_FIELDS = {
    "present",
    "criterion",
    "evidence",
    "decision_weight",
    "decision_effect",
    "confidence",
}

FORBIDDEN_SIGNAL_FIELDS = {
    "truth",
    "hard_signal",
    "risk_score",
    "family_count_no_model",
}

VALID_JUDGMENTS = {"DISCARD", "REVIEW", "KEEP"}
VALID_WEIGHTS = {"hard_discard", "strong_risk", "review_only", "context_only", "protective"}
VALID_EFFECTS = {
    "counted_for_discard",
    "review_only",
    "not_counted",
    "protected_keep",
    "conflict_requires_review",
}
VALID_SECOND_READ_ACTIONS = {"keep", "review", "discard"}
VALID_REVIEW_ROUTING_CLASSES = {
    "auto_keep_candidate",
    "targeted_second_read",
    "human_review",
    "high_conf_discard_candidate",
}
VALID_REVIEW_PRIORITIES = {"low", "medium", "high", "urgent"}
REVIEW_ROUTING_REQUIRED_FIELDS = {
    "second_read_action",
    "review_routing_class",
    "review_reason_code",
    "review_priority",
    "review_exit_criteria",
}


def load_json(path: Path):
    with path.open() as f:
        return json.load(f)


def load_signal_names(path: Path) -> list[str]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        field = "signal_name" if "signal_name" in (reader.fieldnames or []) else "signal"
        signals = []
        for row in reader:
            if row.get("production_safe", "1") in {"1", "true", "TRUE", "yes", "YES"}:
                signals.append(row[field])
    return signals


def load_signal_matrix(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="") as f:
        reader = csv.DictReader(f)
        return {row["respondent_id"]: row for row in reader}


def bool_from_matrix(value: str) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "y"}


def validate(
    chunk_path: Path,
    judgments_path: Path,
    signal_dictionary_path: Path | None,
    signal_matrix_path: Path | None,
    require_review_routing: bool = False,
    max_review_rate: float | None = None,
) -> list[str]:
    errors: list[str] = []

    chunk = load_json(chunk_path)
    judgments = load_json(judgments_path)
    if not isinstance(chunk, list):
        errors.append(f"{chunk_path} must contain a JSON array")
        chunk = []
    if not isinstance(judgments, list):
        errors.append(f"{judgments_path} must contain a JSON array")
        judgments = []

    expected_ids = [row.get("respondent_id") for row in chunk]
    expected_id_set = set(expected_ids)
    seen: set[str] = set()

    if len(judgments) != len(expected_ids):
        errors.append(f"judgment count {len(judgments)} does not match chunk count {len(expected_ids)}")

    if max_review_rate is not None and judgments:
        review_count = sum(1 for row in judgments if isinstance(row, dict) and row.get("agent_judgment") == "REVIEW")
        review_rate = review_count / len(judgments)
        if review_rate > max_review_rate:
            errors.append(
                f"review rate {review_rate:.1%} exceeds max-review-rate {max_review_rate:.1%} "
                f"({review_count}/{len(judgments)} REVIEW)"
            )

    signal_names: list[str] = []
    signal_matrix: dict[str, dict[str, str]] = {}
    if signal_dictionary_path:
        signal_names = load_signal_names(signal_dictionary_path)
    if signal_matrix_path:
        signal_matrix = load_signal_matrix(signal_matrix_path)

    for index, row in enumerate(judgments):
        if not isinstance(row, dict):
            errors.append(f"judgment {index} must be an object")
            continue

        rid = row.get("respondent_id")
        if not rid:
            errors.append(f"judgment {index} is missing respondent_id")
            continue
        if rid in seen:
            errors.append(f"{rid}: duplicate respondent_id")
        seen.add(rid)
        if rid not in expected_id_set:
            errors.append(f"{rid}: respondent_id not found in chunk")

        missing_base = sorted(BASE_REQUIRED_FIELDS - row.keys())
        if missing_base:
            errors.append(f"{rid}: missing required fields {missing_base}")

        if row.get("agent_judgment") not in VALID_JUDGMENTS:
            errors.append(f"{rid}: invalid agent_judgment {row.get('agent_judgment')!r}")

        if require_review_routing:
            missing_review_fields = sorted(REVIEW_ROUTING_REQUIRED_FIELDS - row.keys())
            if missing_review_fields:
                errors.append(f"{rid}: missing review routing fields {missing_review_fields}")
            else:
                if row.get("second_read_action") not in VALID_SECOND_READ_ACTIONS:
                    errors.append(f"{rid}: invalid second_read_action {row.get('second_read_action')!r}")
                if row.get("review_routing_class") not in VALID_REVIEW_ROUTING_CLASSES:
                    errors.append(f"{rid}: invalid review_routing_class {row.get('review_routing_class')!r}")
                if row.get("review_priority") not in VALID_REVIEW_PRIORITIES:
                    errors.append(f"{rid}: invalid review_priority {row.get('review_priority')!r}")
                if not str(row.get("review_reason_code", "")).strip():
                    errors.append(f"{rid}: review_reason_code is blank")
                if not str(row.get("review_exit_criteria", "")).strip():
                    errors.append(f"{rid}: review_exit_criteria is blank")

            judgment = row.get("agent_judgment")
            action = row.get("second_read_action")
            if judgment == "KEEP":
                if action not in {None, "keep"}:
                    errors.append(f"{rid}: KEEP row has second_read_action {action!r}")
                if row.get("review_routing_class") != "auto_keep_candidate":
                    errors.append(f"{rid}: KEEP row must use review_routing_class auto_keep_candidate")
                if not str(row.get("auto_keep_reason", "")).strip():
                    errors.append(f"{rid}: KEEP row missing auto_keep_reason")
            elif judgment == "DISCARD":
                if action not in {None, "discard"}:
                    errors.append(f"{rid}: DISCARD row has second_read_action {action!r}")
                if row.get("review_routing_class") != "high_conf_discard_candidate":
                    errors.append(f"{rid}: DISCARD row must use review_routing_class high_conf_discard_candidate")
                if not str(row.get("discard_candidate_reason", "")).strip() and not str(row.get("disposition_rule_id", "")).strip():
                    errors.append(f"{rid}: DISCARD row missing discard_candidate_reason or disposition_rule_id")
            elif judgment == "REVIEW":
                if action not in {None, "review"}:
                    errors.append(f"{rid}: REVIEW row has second_read_action {action!r}")
                if row.get("review_routing_class") == "auto_keep_candidate":
                    errors.append(f"{rid}: REVIEW row cannot use review_routing_class auto_keep_candidate")
                if row.get("review_routing_class") == "high_conf_discard_candidate":
                    errors.append(f"{rid}: REVIEW row cannot use review_routing_class high_conf_discard_candidate")

        if signal_names:
            assessments = row.get("signal_assessments")
            if not isinstance(assessments, dict):
                errors.append(f"{rid}: missing signal_assessments object")
                continue

            for forbidden in FORBIDDEN_SIGNAL_FIELDS:
                if forbidden in assessments:
                    errors.append(f"{rid}: signal_assessments includes forbidden field {forbidden}")

            missing_signals = [signal for signal in signal_names if signal not in assessments]
            if missing_signals:
                errors.append(f"{rid}: missing {len(missing_signals)} signal assessments, first missing {missing_signals[:5]}")

            matrix_row = signal_matrix.get(rid, {})
            for signal in signal_names:
                assessment = assessments.get(signal)
                if not isinstance(assessment, dict):
                    continue

                missing_signal_fields = sorted(SIGNAL_REQUIRED_FIELDS - assessment.keys())
                if missing_signal_fields:
                    errors.append(f"{rid}/{signal}: missing fields {missing_signal_fields}")
                    continue

                if not isinstance(assessment.get("present"), bool):
                    errors.append(f"{rid}/{signal}: present must be boolean")

                if not str(assessment.get("criterion", "")).strip():
                    errors.append(f"{rid}/{signal}: criterion is blank")

                if not str(assessment.get("evidence", "")).strip():
                    errors.append(f"{rid}/{signal}: evidence is blank")

                if assessment.get("decision_weight") not in VALID_WEIGHTS:
                    errors.append(f"{rid}/{signal}: invalid decision_weight {assessment.get('decision_weight')!r}")

                if assessment.get("decision_effect") not in VALID_EFFECTS:
                    errors.append(f"{rid}/{signal}: invalid decision_effect {assessment.get('decision_effect')!r}")

                try:
                    confidence = float(assessment.get("confidence"))
                    if not 0.0 <= confidence <= 1.0:
                        errors.append(f"{rid}/{signal}: confidence must be 0.0 to 1.0")
                except (TypeError, ValueError):
                    errors.append(f"{rid}/{signal}: confidence must be numeric")

                if matrix_row and signal in matrix_row:
                    expected_present = bool_from_matrix(matrix_row[signal])
                    if assessment.get("present") is not expected_present:
                        errors.append(
                            f"{rid}/{signal}: present={assessment.get('present')!r} does not match signal_matrix={expected_present}"
                        )

            if not row.get("disposition_rule_id"):
                errors.append(f"{rid}: missing disposition_rule_id")

    missing_ids = sorted(expected_id_set - seen)
    if missing_ids:
        errors.append(f"missing judgments for {len(missing_ids)} chunk respondents, first missing {missing_ids[:5]}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("chunk_json", type=Path)
    parser.add_argument("judgments_json", type=Path)
    parser.add_argument("--signal-dictionary", type=Path)
    parser.add_argument("--signal-matrix", type=Path)
    parser.add_argument("--require-review-routing", action="store_true")
    parser.add_argument("--max-review-rate", type=float)
    parser.add_argument("--max-errors", type=int, default=50)
    args = parser.parse_args()
    if args.max_review_rate is not None and not 0.0 <= args.max_review_rate <= 1.0:
        parser.error("--max-review-rate must be a decimal from 0.0 to 1.0")

    errors = validate(
        args.chunk_json,
        args.judgments_json,
        args.signal_dictionary,
        args.signal_matrix,
        args.require_review_routing,
        args.max_review_rate,
    )
    if errors:
        print(f"FAILED: {len(errors)} validation error(s)", file=sys.stderr)
        for error in errors[: args.max_errors]:
            print(f"- {error}", file=sys.stderr)
        if len(errors) > args.max_errors:
            print(f"- ... {len(errors) - args.max_errors} more", file=sys.stderr)
        return 1

    print("OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
