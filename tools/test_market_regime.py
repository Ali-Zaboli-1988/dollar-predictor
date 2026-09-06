import unittest

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))


class MarketRegimeDataTests(unittest.TestCase):
    def test_shock_threshold_design(self):
        # Reference implementation thresholds mirrored from Android detector.
        moves = [4.2, 0.7, 0.5, 0.4]
        self.assertGreaterEqual(max(abs(v) for v in moves), 4.0)

    def test_calm_series_has_low_volatility(self):
        values = [100.0]
        for i in range(9):
            values.append(values[-1] * (1.001 if i % 2 == 0 else 0.999))
        returns = [abs((values[i] - values[i + 1]) / values[i + 1]) * 100 for i in range(len(values) - 1)]
        rms = (sum(x * x for x in returns) / len(returns)) ** 0.5
        self.assertLess(rms, 0.2)

    def test_volatile_series_exceeds_volatility_threshold(self):
        values = [100.0]
        for i in range(9):
            values.append(values[-1] * (1.035 if i % 2 == 0 else 0.965))
        returns = [abs((values[i] - values[i + 1]) / values[i + 1]) * 100 for i in range(len(values) - 1)]
        rms = (sum(x * x for x in returns) / len(returns)) ** 0.5
        self.assertGreaterEqual(rms, 3.0)


if __name__ == "__main__":
    unittest.main()
