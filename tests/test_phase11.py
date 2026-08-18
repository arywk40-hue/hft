import unittest

from pathlib import Path


class Phase11ReviewTests(unittest.TestCase):
    def test_integrated_facts_preserve_scope(self):
        import json
        facts = json.loads(Path("results/phase11/integrated_facts.json").read_text())
        self.assertEqual(facts["expected_development_days"], 85)
        self.assertEqual(facts["available_development_days"], 70)
        self.assertEqual(facts["missing_development_days"], 15)
        self.assertFalse(facts["holdout_processed"])


if __name__ == "__main__":
    unittest.main()
