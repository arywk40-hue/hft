import unittest

import numpy as np

from src.analytics.candidates import candidate_series


class Phase8CandidateTests(unittest.TestCase):
    def test_candidate_warmup_is_day_local(self):
        price = np.arange(1.0, 101.0)
        result = candidate_series(price, "rolling_mean", 5)
        self.assertTrue(np.isnan(result[3]))
        self.assertTrue(np.isfinite(result[4]))

    def test_return_candidate_does_not_invent_pre_warmup_values(self):
        price = np.exp(np.linspace(0, 1, 100))
        result = candidate_series(price, "realized_volatility", 5)
        self.assertTrue(np.isnan(result[4]))
        self.assertTrue(np.isfinite(result[5]))


if __name__ == "__main__":
    unittest.main()
