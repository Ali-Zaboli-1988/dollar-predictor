from pathlib import Path
import tempfile
import unittest

from calibrate_weights import FACTORS, evaluate, load_rows


class CalibratorTests(unittest.TestCase):
    def _write_csv(self, text: str) -> Path:
        handle = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
        handle.write(text)
        handle.close()
        return Path(handle.name)

    def test_load_rows_requires_all_factor_columns(self):
        header = "close," + ",".join(FACTORS[:-1]) + "\n"
        path = self._write_csv(header + "100,1,1,1,1,1\n")
        with self.assertRaises(ValueError):
            load_rows(path)

    def test_evaluate_directional_signal(self):
        header = "close," + ",".join(FACTORS) + "\n"
        lines = []
        for i in range(25):
            close = 100 + i
            factors = [1, 0, 0, 0, 0, 0]
            lines.append(str(close) + "," + ",".join(map(str, factors)) + "\n")
        path = self._write_csv(header + "".join(lines))
        rows = load_rows(path)
        metrics = evaluate(rows, (1, 0, 0, 0, 0, 0), threshold=0.5, min_move=0.003)
        self.assertGreaterEqual(metrics.samples, 20)
        self.assertEqual(metrics.hits, metrics.samples)
        self.assertAlmostEqual(metrics.accuracy, 100.0)

    def test_no_signal_can_be_zero_coverage(self):
        header = "close," + ",".join(FACTORS) + "\n"
        lines = []
        for i in range(25):
            lines.append("100," + ",".join(["0"] * len(FACTORS)) + "\n")
        path = self._write_csv(header + "".join(lines))
        rows = load_rows(path)
        metrics = evaluate(rows, (1, 1, 1, 1, 1, 1), threshold=1.0, min_move=0.003)
        self.assertEqual(metrics.samples, 0)
        self.assertEqual(metrics.coverage, 0.0)


if __name__ == "__main__":
    unittest.main()
