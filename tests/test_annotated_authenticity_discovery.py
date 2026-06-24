import tempfile
import unittest
import importlib.util
import sys
from pathlib import Path

import pandas as pd

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "reporting-survey-quality"
    / "scripts"
    / "build_annotated_authenticity_discovery.py"
)
spec = importlib.util.spec_from_file_location("build_annotated_authenticity_discovery", SCRIPT_PATH)
discovery = importlib.util.module_from_spec(spec)
assert spec.loader is not None
sys.modules[spec.name] = discovery
spec.loader.exec_module(discovery)


class AnnotatedAuthenticityDiscoveryTests(unittest.TestCase):
    def test_leakage_columns_exclude_helper_fields(self):
        columns = [
            "status",
            "markers",
            "conditionsTFG",
            "noanswerq5_r3",
            "qc5r2",
            "VALIDCLIENT",
            "CHANNELTRACKING",
            "closingemail",
            "RD_Searchr0",
            "qcoe1",
            "q34",
            "CLASSIFYGROUP",
        ]

        leaked = set(discovery.leakage_columns(columns))

        for column in columns[:9]:
            self.assertIn(column, leaked)
        self.assertNotIn("qcoe1", leaked)
        self.assertNotIn("q34", leaked)
        self.assertNotIn("CLASSIFYGROUP", leaked)

    def test_labeled_manifest_reconciles_status_rows_once(self):
        rows = pd.DataFrame(
            {
                "__dataset_id": ["d01", "d01", "d01"],
                "__dataset_name": ["toy.xlsx", "toy.xlsx", "toy.xlsx"],
                "__source_file": ["/tmp/toy.xlsx"] * 3,
                "__source_row_number": [2, 3, 4],
                "__respondent_id": ["a", "b", "c"],
                "__status_clean": ["3", "5", "3"],
                "status": ["3", "5", "3"],
                "qcoe1": ["built decks", "asdf", "plumbing"],
            }
        )
        corpus = discovery.Corpus(rows=rows, inventory=[], leakage={"d01": ["status"]}, question_rows=[])

        with tempfile.TemporaryDirectory() as tmp:
            labeled, accepted, rejected = discovery.write_split_and_ledgers(corpus, None, Path(tmp))
            manifest = pd.read_csv(Path(tmp) / "labeled_row_manifest.csv")

        self.assertEqual(len(labeled), 3)
        self.assertEqual(len(accepted), 2)
        self.assertEqual(len(rejected), 1)
        self.assertEqual(manifest["row_key"].duplicated().sum(), 0)
        self.assertEqual(manifest["status"].astype(str).value_counts().to_dict(), {"3": 2, "5": 1})

    def test_missing_count_does_not_double_count_blank_nan(self):
        series = pd.Series(["", None, float("nan"), "answer"])
        missing = int(series.map(discovery.text).eq("").sum())
        self.assertEqual(missing, 3)


if __name__ == "__main__":
    unittest.main()
