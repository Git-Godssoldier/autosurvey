import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "reporting-survey-quality"
    / "scripts"
    / "build_semantic_authenticity_loop.py"
)
spec = importlib.util.spec_from_file_location("build_semantic_authenticity_loop", SCRIPT_PATH)
semantic = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = semantic
spec.loader.exec_module(semantic)


class SemanticAuthenticityLoopTests(unittest.TestCase):
    def test_datamap_field_line_parser(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "toy.xlsx"
            pd.DataFrame({0: ["[qcoe1]: Describe your work role", "Values: 1-2"]}).to_excel(
                path, sheet_name="Datamap", header=False, index=False
            )

            mapping = semantic.read_datamap(path)

        self.assertEqual(mapping["qcoe1"], "Describe your work role")

    def test_client_context_stays_separate_from_blind_tier(self):
        features = pd.DataFrame(
            {
                "dataset_id": ["d01"],
                "source_row_number": [2],
                "semantic_risk_score": [0.0],
                "blind_tier": [1],
            }
        )
        with tempfile.TemporaryDirectory() as tmp:
            prior = Path(tmp) / "prior"
            artifacts = prior / "model_artifacts"
            artifacts.mkdir(parents=True)
            pd.DataFrame(
                {
                    "dataset_id": ["d01"],
                    "respondent_id": ["r1"],
                    "source_row_number": [2],
                    "status": [5],
                    "client_reject_probability": [0.99],
                    "operational_tier": ["Exclude candidate"],
                }
            ).to_csv(artifacts / "leave_one_dataset_predictions.csv", index=False)
            updated = semantic.attach_client_rejection_context(features, prior, Path(tmp))

        self.assertEqual(int(updated.loc[0, "blind_tier"]), 1)
        self.assertEqual(updated.loc[0, "client_process_routing_tier"], "Tier 5 Exclude candidate")
        self.assertGreater(float(updated.loc[0, "client_reject_probability"]), 0.9)


if __name__ == "__main__":
    unittest.main()
