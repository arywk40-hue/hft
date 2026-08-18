import unittest

import numpy as np

from src.analytics.predictive import benjamini_hochberg, forward_indices


class Phase9PredictiveTests(unittest.TestCase):
    def test_forward_alignment_requires_exact_timestamp(self):
        seconds = np.array([0, 1, 3, 4])
        indices = forward_indices(seconds, 1)
        np.testing.assert_array_equal(indices, np.array([1, -1, 3, -1]))

    def test_fdr_returns_same_length_and_rejects_small_pvalues(self):
        reject, q = benjamini_hochberg(np.array([.0001, .9, .8]), .05)
        self.assertEqual(len(reject), 3)
        self.assertTrue(reject[0])
        self.assertTrue(np.isfinite(q[0]))


if __name__ == "__main__":
    unittest.main()
