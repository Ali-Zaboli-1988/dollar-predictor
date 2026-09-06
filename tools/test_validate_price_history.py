#!/usr/bin/env python3

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from validate_price_history import validate


class ValidatePriceHistoryTest(unittest.TestCase):
    def write(self, text: str) -> Path:
        tmp = tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8")
        with tmp:
            tmp.write(text)
        return Path(tmp.name)

    def test_valid_history(self) -> None:
        path = self.write("date,close\n2026-09-01,214000\n2026-09-02,219900\n2026-09-03,221060\n")
        count, first_day, last_day, largest = validate(path, 3)
        self.assertEqual(count, 3)
        self.assertEqual(first_day.isoformat(), "2026-09-01")
        self.assertEqual(last_day.isoformat(), "2026-09-03")
        self.assertGreater(largest, 0.0)

    def test_duplicate_dates_rejected(self) -> None:
        path = self.write("date,close\n2026-09-01,214000\n2026-09-01,215000\n")
        with self.assertRaisesRegex(ValueError, "duplicate dates"):
            validate(path, 2)

    def test_descending_dates_rejected(self) -> None:
        path = self.write("date,close\n2026-09-02,219900\n2026-09-01,214000\n")
        with self.assertRaisesRegex(ValueError, "ascending order"):
            validate(path, 2)

    def test_implausible_move_rejected(self) -> None:
        path = self.write("date,close\n2026-09-01,214000\n2026-09-02,400000\n")
        with self.assertRaisesRegex(ValueError, "implausible daily move"):
            validate(path, 2)

    def test_wrong_schema_rejected(self) -> None:
        path = self.write("day,value\n2026-09-01,214000\n")
        with self.assertRaisesRegex(ValueError, "unexpected columns"):
            validate(path, 1)


if __name__ == "__main__":
    unittest.main()
