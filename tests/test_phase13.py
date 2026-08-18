import hashlib
import json
import unittest
from pathlib import Path


class Phase13HoldoutTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[1]

    def test_holdout_filter_excludes_development_and_post_holdout(self):
        scope = json.loads((self.root / "results/holdout/phase13_scope.json").read_text())
        self.assertEqual(scope["processed_day_ids"], list(range(86, 109)))
        self.assertEqual(scope["excluded_day_ranges"], [[1, 85], [109, 123]])
        self.assertEqual(scope["holdout_expected_days"], 23)

    def test_freeze_is_unchanged_and_manifest_matches(self):
        freeze = self.root / "results/freeze/development_freeze.json"
        manifest = json.loads((self.root / "results/holdout/freeze_manifest.json").read_text())
        digest = hashlib.sha256(freeze.read_bytes()).hexdigest()
        self.assertEqual(digest, manifest["freeze_file_sha256"])
        self.assertEqual(manifest["holdout_expected_days"], 23)

    def test_integrity_and_schema_cover_exact_holdout_days(self):
        import pandas as pd
        expected = set(range(86, 109))
        integrity = pd.read_csv(self.root / "results/holdout/integrity.csv")
        schema = pd.read_csv(self.root / "results/holdout/schema.csv")
        self.assertEqual(set(integrity.day), expected)
        self.assertEqual(set(schema.day), expected)
        self.assertEqual(integrity.status.tolist().count("valid"), 23)
        self.assertEqual(schema.status.tolist().count("valid"), 23)

    def test_required_holdout_outputs_and_separation(self):
        import pandas as pd
        required = {
            "integrity.csv", "schema.csv", "missingness.csv", "window_generalization.csv",
            "feature_hypothesis_validation.csv", "ic_validation.csv", "regime_validation.csv",
            "distribution_validation.csv", "pca_validation.csv", "holdout_summary.csv",
        }
        output = self.root / "results/holdout"
        self.assertTrue(required.issubset({path.name for path in output.iterdir()}))
        self.assertNotIn(85, set(pd.read_csv(output / "regime_validation.csv").day))


if __name__ == "__main__":
    unittest.main()
