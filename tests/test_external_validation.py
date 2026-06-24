import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "reporting-survey-quality"
    / "scripts"
    / "external_validation_core.py"
)
spec = importlib.util.spec_from_file_location("external_validation_core", SCRIPT_PATH)
external = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = external
spec.loader.exec_module(external)


class ExternalValidationTests(unittest.TestCase):
    def test_confusion_metrics_positive_class(self):
        y = np.array([1, 1, 0, 0])
        pred = np.array([1, 0, 1, 0])
        metrics = external.confusion_metrics(y, pred)
        self.assertEqual(metrics["tp"], 1)
        self.assertEqual(metrics["fp"], 1)
        self.assertEqual(metrics["tn"], 1)
        self.assertEqual(metrics["fn"], 1)
        self.assertAlmostEqual(metrics["precision_ppv"], 0.5)
        self.assertAlmostEqual(metrics["sensitivity_recall"], 0.5)

    def test_auprc_prevalence_baseline_is_reportable(self):
        y = np.array([1, 0, 0, 0])
        score = np.array([0.9, 0.8, 0.2, 0.1])
        self.assertAlmostEqual(float(y.mean()), 0.25)
        self.assertGreaterEqual(external.average_precision(y, score), 0.25)

    def test_prediction_hash_changes_when_score_changes(self):
        row_a = {"respondent_id": "a", "client_reject_probability": 0.1}
        row_b = {"respondent_id": "a", "client_reject_probability": 0.2}
        self.assertNotEqual(external.sha256_text(str(row_a)), external.sha256_text(str(row_b)))

    def test_evaluator_refuses_missing_seal(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit):
                external.validate_seal(Path(tmp))

    def test_evaluator_refuses_tampered_prediction_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            pred = out / "predictions_preunblind.csv"
            pred.write_text("respondent_id,client_reject_probability\n1,0.1\n")
            seal = {
                "files": {"predictions_preunblind.csv": external.sha256_file(pred)},
                "state": "SEALED_PENDING_UNBLIND",
            }
            external.write_json(out / "prediction_seal_manifest.json", seal)
            pred.write_text("respondent_id,client_reject_probability\n1,0.9\n")
            with self.assertRaises(SystemExit):
                external.validate_seal(out)

    def test_join_uses_stable_id_not_row_order(self):
        pred = pd.DataFrame({"respondent_id": ["a", "b"], "score": [0.1, 0.9]})
        labels = pd.DataFrame({"respondent_id": ["b", "a"], "client_label": [1, 0]})
        joined = pred.merge(labels, on="respondent_id", how="inner")
        self.assertEqual(joined.loc[joined["respondent_id"].eq("a"), "client_label"].iloc[0], 0)
        self.assertEqual(joined.loc[joined["respondent_id"].eq("b"), "client_label"].iloc[0], 1)

    def test_duplicate_ids_are_detectable(self):
        df = pd.DataFrame({"respondent_id": ["a", "a", "b"]})
        self.assertEqual(int(df["respondent_id"].duplicated().sum()), 1)

    def test_status_to_label_mapping(self):
        self.assertEqual(external.status_to_label("5"), 1)
        self.assertEqual(external.status_to_label("3"), 0)
        self.assertIsNone(external.status_to_label("2"))

    def test_gitignore_blocks_client_outputs(self):
        ignore = (Path(__file__).resolve().parents[1] / ".gitignore").read_text()
        self.assertIn("*.xlsx", ignore)
        self.assertIn("outputs/", ignore)


if __name__ == "__main__":
    unittest.main()
