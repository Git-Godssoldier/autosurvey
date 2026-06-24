import csv
import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SEMANTIC_SKILL = REPO / "skills" / "reviewing-survey-authenticity"
EVALUATOR_PATH = (
    REPO
    / "skills"
    / "evaluating-survey-authenticity"
    / "scripts"
    / "evaluator_boundary.py"
)

spec = importlib.util.spec_from_file_location("evaluator_boundary", EVALUATOR_PATH)
evaluator = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = evaluator
spec.loader.exec_module(evaluator)


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


class AgentNativeBoundaryTests(unittest.TestCase):
    def test_semantic_skill_has_no_scripts_dir(self):
        self.assertTrue(SEMANTIC_SKILL.exists())
        self.assertFalse((SEMANTIC_SKILL / "scripts").exists())

    def test_semantic_skill_has_required_references(self):
        required = {
            "workflow.md",
            "question-contracts.md",
            "semantic-signal-bank.md",
            "accepted-respondent-guardrails.md",
            "decision-rubric.md",
            "relationship-patterns.md",
            "validated-case-patterns.md",
            "provisional-hypotheses.md",
            "failed-hypotheses.md",
            "output-schema.md",
        }
        actual = {path.name for path in (SEMANTIC_SKILL / "references").glob("*.md")}
        self.assertEqual(required, actual)

    def test_semantic_skill_does_not_embed_status_literals_or_row_ids(self):
        combined = "\n".join(path.read_text() for path in SEMANTIC_SKILL.rglob("*.md"))
        lowered = combined.lower()
        self.assertNotIn("status = 5", lowered)
        self.assertNotIn("status=5", lowered)
        self.assertNotIn("status = 3", lowered)
        self.assertNotIn("status=3", lowered)
        self.assertNotRegex(combined, r"\b[0-9a-f]{16,}\b")

    def test_evaluator_refuses_unsealed_ledger(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(evaluator.EvaluatorBoundaryError, "BLOCKED_UNSEALED_LEDGER"):
                evaluator.validate_seal(Path(tmp))

    def test_post_seal_hash_detects_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            run_dir = Path(tmp)
            ledger = run_dir / "blind_semantic_ledger.csv"
            ledger.write_text("respondent_stable_id,decision_tier\nr1,Tier 1\n")
            evaluator.write_seal_manifest(run_dir, ["blind_semantic_ledger.csv"])
            evaluator.validate_seal(run_dir)
            ledger.write_text("respondent_stable_id,decision_tier\nr1,Tier 5\n")
            with self.assertRaisesRegex(evaluator.EvaluatorBoundaryError, "SEAL_HASH_MISMATCH"):
                evaluator.validate_seal(run_dir)

    def test_stable_id_join_not_row_order(self):
        predictions = [
            {"respondent_stable_id": "a", "discard_recommendation": "false"},
            {"respondent_stable_id": "b", "discard_recommendation": "true"},
        ]
        labels = [
            {"respondent_stable_id": "b", "client_label": "5"},
            {"respondent_stable_id": "a", "client_label": "3"},
        ]
        joined = evaluator.join_by_stable_id(
            predictions,
            labels,
            id_column="respondent_stable_id",
            label_column="client_label",
        )
        by_id = {row["respondent_stable_id"]: row for row in joined}
        self.assertEqual(by_id["a"]["client_label"], "3")
        self.assertEqual(by_id["b"]["client_label"], "5")

    def test_duplicate_stable_ids_fail(self):
        predictions = [
            {"respondent_stable_id": "a", "discard_recommendation": "false"},
            {"respondent_stable_id": "a", "discard_recommendation": "true"},
        ]
        labels = [{"respondent_stable_id": "a", "client_label": "3"}]
        with self.assertRaisesRegex(evaluator.EvaluatorBoundaryError, "STABLE_ID_DUPLICATE"):
            evaluator.join_by_stable_id(
                predictions,
                labels,
                id_column="respondent_stable_id",
                label_column="client_label",
            )

    def test_client_reject_status_is_positive_class(self):
        self.assertEqual(evaluator.status_to_positive("5"), 1)
        self.assertEqual(evaluator.status_to_positive("3"), 0)
        counts = evaluator.confusion_counts([1, 1, 0, 0], [1, 0, 1, 0])
        self.assertEqual(counts, {"tp": 1, "fp": 1, "tn": 1, "fn": 1})

    def test_evaluator_cannot_write_decision_columns(self):
        before = [
            {
                "respondent_stable_id": "r1",
                "decision_tier": "Tier 1",
                "discard_recommendation": "false",
            }
        ]
        after = [
            {
                "respondent_stable_id": "r1",
                "decision_tier": "Tier 5",
                "discard_recommendation": "true",
            }
        ]
        with self.assertRaisesRegex(evaluator.EvaluatorBoundaryError, "EVALUATOR_WROTE_DECISION_COLUMN"):
            evaluator.assert_decision_columns_unchanged(before, after, id_column="respondent_stable_id")

    def test_preseal_scripted_inference_attempt_fails(self):
        with self.assertRaisesRegex(evaluator.EvaluatorBoundaryError, "FAILED_SCRIPTED_INFERENCE_FIREWALL"):
            evaluator.assert_preseal_command_allowed("python score_rows.py --read_excel respondent_file.xlsx")

    def test_ledger_requires_rationale_decision_signals_and_protection(self):
        rows = [
            {
                "respondent_stable_id": "r1",
                "source_row_reference": "row 2",
                "decision_tier": "Tier 2",
                "discard_recommendation": "false",
                "forensic_rationale": "A weak concern is visible.",
                "human_advocate_countercase": "The response remains coherent.",
                "evidence_judge_summary": "Keep with note.",
                "suspicious_signal_families": "speed-content coupling",
                "protective_evidence": "",
                "question_chain_citations": "row 2, q1",
            }
        ]
        with self.assertRaisesRegex(evaluator.EvaluatorBoundaryError, "LEDGER_ROW_1_MISSING"):
            evaluator.validate_required_ledger_fields(rows)

    def test_public_output_contract_exactly_two_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp) / "public"
            public.mkdir()
            (public / "AUTOSURVEY_RESULTS.xlsx").write_text("placeholder")
            (public / "AUTOSURVEY_EVOLUTION.md").write_text("placeholder")
            evaluator.assert_public_outputs_exactly(Path(tmp))
            (public / "extra.csv").write_text("placeholder")
            with self.assertRaisesRegex(evaluator.EvaluatorBoundaryError, "PUBLIC_OUTPUT_CONTRACT"):
                evaluator.assert_public_outputs_exactly(Path(tmp))


if __name__ == "__main__":
    unittest.main()
