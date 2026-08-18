import unittest

import numpy as np

from src.analytics.redundancy import day_zscore, deterministic_rows


class Phase10RedundancyTests(unittest.TestCase):
    def test_day_zscore_does_not_fill_nan(self):
        values = np.array([[1.0, np.nan], [2.0, 3.0], [3.0, 4.0]])
        result = day_zscore(values)
        self.assertTrue(np.isnan(result[0, 1]))
        self.assertAlmostEqual(float(np.nanmean(result[:, 0])), 0.0)

    def test_row_cap_is_deterministic(self):
        values = np.arange(100).reshape(50, 2)
        np.testing.assert_array_equal(deterministic_rows(values, 5), deterministic_rows(values, 5))


if __name__ == "__main__":
    unittest.main()
