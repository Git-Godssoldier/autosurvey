"""Post-seal evaluator guardrails for Autosurvey authenticity runs.

This module is intentionally limited to integrity checks, stable-ID joins,
and metrics after an agent-authored blind ledger is sealed.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Iterable

DECISION_COLUMNS = {
    "decision_tier",
    "discard_recommendation",
    "authenticity_risk",
    "client_rejection_probability",
    "reviewer_confidence",
    "forensic_rationale",
    "human_advocate_countercase",
    "evidence_judge_summary",
    "suspicious_signal_families",
    "protective_evidence",
    "question_chain_citations",
    "open_end_citations",
    "matrix_or_scale_citations",
    "timing_or_route_citations",
    "technical_context_citations",
}

FORBIDDEN_PRESEAL_TERMS = {
    "read_excel",
    "read_csv",
    "openpyxl",
    "pandas",
    "dataframe",
    "regex",
    "similarity",
    "predict",
    "score",
    "word_count",
    "packet",
    "feature",
}


class EvaluatorBoundaryError(RuntimeError):
    """Raised when a post-seal evaluator boundary is violated."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_seal(run_dir: Path) -> dict:
    manifest_path = run_dir / "decision_seal_manifest.json"
    if not manifest_path.exists():
        raise EvaluatorBoundaryError("BLOCKED_UNSEALED_LEDGER")
    manifest = json.loads(manifest_path.read_text())
    if manifest.get("state") != "SEALED_PENDING_LABEL_REVEAL":
        raise EvaluatorBoundaryError("BLOCKED_UNSEALED_LEDGER")
    files = manifest.get("files") or {}
    if not files:
        raise EvaluatorBoundaryError("BLOCKED_UNSEALED_LEDGER")
    for name, expected_hash in files.items():
        actual_path = run_dir / name
        if not actual_path.exists():
            raise EvaluatorBoundaryError(f"SEAL_FILE_MISSING:{name}")
        if sha256_file(actual_path) != expected_hash:
            raise EvaluatorBoundaryError(f"SEAL_HASH_MISMATCH:{name}")
    return manifest


def write_seal_manifest(run_dir: Path, file_names: Iterable[str]) -> Path:
    files = {name: sha256_file(run_dir / name) for name in file_names}
    manifest = {"state": "SEALED_PENDING_LABEL_REVEAL", "files": files}
    path = run_dir / "decision_seal_manifest.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return path


def read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def join_by_stable_id(
    predictions: list[dict[str, str]],
    labels: list[dict[str, str]],
    *,
    id_column: str,
    label_column: str,
) -> list[dict[str, str]]:
    pred_ids = [row.get(id_column, "") for row in predictions]
    label_ids = [row.get(id_column, "") for row in labels]
    if "" in pred_ids or "" in label_ids:
        raise EvaluatorBoundaryError("STABLE_ID_MISSING")
    if len(set(pred_ids)) != len(pred_ids) or len(set(label_ids)) != len(label_ids):
        raise EvaluatorBoundaryError("STABLE_ID_DUPLICATE")
    labels_by_id = {row[id_column]: row for row in labels}
    joined = []
    for row in predictions:
        rid = row[id_column]
        if rid not in labels_by_id:
            raise EvaluatorBoundaryError(f"STABLE_ID_NO_LABEL:{rid}")
        joined.append({**row, label_column: labels_by_id[rid][label_column]})
    return joined


def status_to_positive(value: object) -> int | None:
    text = str(value).strip()
    if text == "5":
        return 1
    if text == "3":
        return 0
    return None


def confusion_counts(y_true: Iterable[int], y_pred: Iterable[int]) -> dict[str, int]:
    counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    for actual, predicted in zip(y_true, y_pred):
        if actual == 1 and predicted == 1:
            counts["tp"] += 1
        elif actual == 0 and predicted == 1:
            counts["fp"] += 1
        elif actual == 0 and predicted == 0:
            counts["tn"] += 1
        elif actual == 1 and predicted == 0:
            counts["fn"] += 1
        else:
            raise EvaluatorBoundaryError("INVALID_BINARY_LABEL")
    return counts


def assert_decision_columns_unchanged(
    before: list[dict[str, str]],
    after: list[dict[str, str]],
    *,
    id_column: str,
) -> None:
    after_by_id = {row[id_column]: row for row in after}
    for before_row in before:
        rid = before_row[id_column]
        if rid not in after_by_id:
            raise EvaluatorBoundaryError(f"DECISION_ROW_MISSING:{rid}")
        after_row = after_by_id[rid]
        for column in DECISION_COLUMNS:
            if before_row.get(column, "") != after_row.get(column, ""):
                raise EvaluatorBoundaryError(f"EVALUATOR_WROTE_DECISION_COLUMN:{column}")


def validate_required_ledger_fields(rows: list[dict[str, str]]) -> None:
    required = {
        "respondent_stable_id",
        "source_row_reference",
        "decision_tier",
        "discard_recommendation",
        "forensic_rationale",
        "human_advocate_countercase",
        "evidence_judge_summary",
        "suspicious_signal_families",
        "protective_evidence",
        "question_chain_citations",
    }
    for index, row in enumerate(rows, start=1):
        missing = [column for column in required if not row.get(column)]
        if missing:
            raise EvaluatorBoundaryError(f"LEDGER_ROW_{index}_MISSING:{','.join(sorted(missing))}")


def assert_public_outputs_exactly(run_dir: Path) -> None:
    public_dir = run_dir / "public"
    files = sorted(path.name for path in public_dir.iterdir() if path.is_file())
    expected = ["AUTOSURVEY_EVOLUTION.md", "AUTOSURVEY_RESULTS.xlsx"]
    if files != expected:
        raise EvaluatorBoundaryError(f"PUBLIC_OUTPUT_CONTRACT:{files}")


def assert_preseal_command_allowed(command: str) -> None:
    lowered = command.lower()
    matched = sorted(term for term in FORBIDDEN_PRESEAL_TERMS if term in lowered)
    if matched:
        raise EvaluatorBoundaryError(f"FAILED_SCRIPTED_INFERENCE_FIREWALL:{','.join(matched)}")
