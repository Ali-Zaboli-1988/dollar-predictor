import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import build_news_features as builder


class NewsFeatureTests(unittest.TestCase):
    def test_classification_is_deterministic(self):
        result = builder.classify("Iran sanctions increase as ceasefire talks stall and dollar intervention begins")
        self.assertEqual(result["sanctions"], 1)
        self.assertEqual(result["diplomacy"], -1)
        self.assertEqual(result["currency"], -1)

    def test_load_prices_requires_date_and_close(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "bad.csv"
            path.write_text("date,open\n2026-09-01,100\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "close"):
                builder.load_prices(path)

    @patch("build_news_features.fetch_gdelt")
    def test_build_aligns_features_to_price_rows(self, fetch_mock):
        fetch_mock.return_value = [
            "Iran sanctions rise as negotiations pause",
            "Oil shipping risk increases near Strait of Hormuz",
        ]
        prices = [
            {"date": "2026-09-01", "close": "100.0"},
        ]
        result = builder.build(prices, sleep_seconds=0)
        self.assertEqual(result[0]["date"], "2026-09-01")
        self.assertEqual(result[0]["close"], "100.0")
        self.assertEqual(result[0]["sanctions"], "1")
        self.assertEqual(result[0]["diplomacy"], "-1")
        self.assertEqual(result[0]["oil"], "1")


if __name__ == "__main__":
    unittest.main()
