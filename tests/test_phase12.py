import json
import unittest
from pathlib import Path


class Phase12FreezeTests(unittest.TestCase):
    def test_freeze_is_development_only(self):
        record = json.loads(Path("results/freeze/development_freeze.json").read_text())
        self.assertEqual(record["scope"]["available_development_days"], 70)
        self.assertEqual(record["scope"]["missing_day_ids"], list(range(65, 80)))
        self.assertFalse(record["scope"]["holdout_processed"])


if __name__ == "__main__":
    unittest.main()
