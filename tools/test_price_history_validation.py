import csv
import tempfile
import unittest
from pathlib import Path

from validate_price_history import validate


class TestValidatePriceHistory(unittest.TestCase):
    def write_csv(self, rows):
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8", newline=""
        )
        self.addCleanup(lambda: Path(f.name).unlink(missing_ok=True))
        writer = csv.writer(f)
        writer.writerow(["date", "close"])
        writer.writerows(rows)
        f.close()
        return f.name

    def test_valid_series(self):
        path = self.write_csv([
            ["2026-06-01", "100000"],
            ["2026-06-02", "101000"],
            ["2026-06-03", "100500"],
        ])
        result = validate(path, minimum_rows=3)
        self.assertEqual(result.rows, 3)
        self.assertEqual(result.first_date.isoformat(), "2026-06-01")
        self.assertEqual(result.last_date.isoformat(), "2026-06-03")

    def test_scientific_notation_integer_is_accepted(self):
        path = self.write_csv([
            ["2026-06-01", "1e+06"],
            ["2026-06-02", "1010000"],
            ["2026-06-03", "1005000"],
        ])
        result = validate(path, minimum_rows=3)
        self.assertEqual(result.rows, 3)
        self.assertEqual(result.first_date.isoformat(), "2026-06-01")

    def test_non_integer_price_is_rejected(self):
        path = self.write_csv([
            ["2026-06-01", "100000.5"],
            ["2026-06-02", "101000"],
            ["2026-06-03", "100500"],
        ])
        with self.assertRaises(ValueError):
            validate(path, minimum_rows=3)

    def test_duplicate_date_is_rejected(self):
        path = self.write_csv([
            ["2026-06-01", "100000"],
            ["2026-06-01", "101000"],
            ["2026-06-03", "100500"],
        ])
        with self.assertRaises(ValueError):
            validate(path, minimum_rows=3)

    def test_unsorted_dates_are_rejected(self):
        path = self.write_csv([
            ["2026-06-02", "100000"],
            ["2026-06-01", "101000"],
            ["2026-06-03", "100500"],
        ])
        with self.assertRaises(ValueError):
            validate(path, minimum_rows=3)

    def test_large_jump_is_rejected(self):
        path = self.write_csv([
            ["2026-06-01", "100000"],
            ["2026-06-02", "130000"],
            ["2026-06-03", "131000"],
        ])
        with self.assertRaises(ValueError):
            validate(path, minimum_rows=3, max_daily_change_pct=25.0)

    def test_custom_jump_threshold_is_respected(self):
        path = self.write_csv([
            ["2026-06-01", "100000"],
            ["2026-06-02", "105000"],
            ["2026-06-03", "106000"],
        ])
        with self.assertRaises(ValueError):
            validate(path, minimum_rows=3, max_daily_change_pct=4.0)

    def test_non_positive_price_is_rejected(self):
        path = self.write_csv([
            ["2026-06-01", "100000"],
            ["2026-06-02", "0"],
            ["2026-06-03", "101000"],
        ])
        with self.assertRaises(ValueError):
            validate(path, minimum_rows=3)


if __name__ == "__main__":
    unittest.main()
