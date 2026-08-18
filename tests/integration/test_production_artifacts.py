import hashlib
import json
import unittest
from pathlib import Path


class ProductionArtifactTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(__file__).resolve().parents[2]

    def test_final_reports_and_artifact_index_exist(self):
        self.assertTrue((self.root / "reports/final_report.md").is_file())
        self.assertTrue((self.root / "reports/reproducibility.md").is_file())
        self.assertTrue((self.root / "reports/artifact_index.md").is_file())

    def test_freeze_hash_and_scope_remain_intact(self):
        freeze = self.root / "results/freeze/development_freeze.json"
        manifest = json.loads((self.root / "results/holdout/freeze_manifest.json").read_text())
        self.assertEqual(hashlib.sha256(freeze.read_bytes()).hexdigest(), manifest["freeze_file_sha256"])
        scope = json.loads((self.root / "results/holdout/phase13_scope.json").read_text())
        self.assertEqual(scope["processed_day_ids"], list(range(86, 109)))
        self.assertEqual(scope["excluded_day_ranges"], [[1, 85], [109, 123]])


if __name__ == "__main__":
    unittest.main()
