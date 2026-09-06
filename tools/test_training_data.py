import tempfile
import unittest
from pathlib import Path

import validate_training_data as validator


class TrainingDataValidationTests(unittest.TestCase):
    HEADER = "date,close,war,sanctions,oil,diplomacy,currency,economy\n"

    def test_accepts_valid_chronological_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "valid.csv"
            rows = "".join(
                f"2026-01-{day:02d},{100+day},1,0,0,0,0,1\n"
                for day in range(1, 21)
            )
            path.write_text(self.HEADER + rows, encoding="utf-8")
            count, errors = validator.validate(path)
            self.assertEqual(count, 20)
            self.assertEqual(errors, [])

    def test_rejects_non_increasing_dates(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            rows = "".join(
                f"2026-01-{day:02d},{100+day},1,0,0,0,0,1\n"
                for day in range(1, 20)
            )
            rows += "2026-01-19,120,1,0,0,0,0,1\n"
            path.write_text(self.HEADER + rows, encoding="utf-8")
            _, errors = validator.validate(path)
            self.assertTrue(any("strictly increasing" in error for error in errors))

    def test_rejects_invalid_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad_close.csv"
            rows = "".join(
                f"2026-01-{day:02d},{0 if day == 5 else 100+day},1,0,0,0,0,1\n"
                for day in range(1, 21)
            )
            path.write_text(self.HEADER + rows, encoding="utf-8")
            _, errors = validator.validate(path)
            self.assertTrue(any("close must be" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
