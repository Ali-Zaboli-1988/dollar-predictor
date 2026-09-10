import csv
import json
import tempfile
import unittest
from pathlib import Path

import build_news_features_timeline as builder


class OfflineNewsFeatureTests(unittest.TestCase):
    def test_fixture_normalization_and_lag_are_deterministic(self):
        fixture_path = Path(__file__).parent.parent / "data" / "experimental" / "gdelt_timeline_fixture.json"
        with fixture_path.open("r", encoding="utf-8") as fh:
            fixture = json.load(fh)

        prices = [
            {"date": "2026-09-02", "close": "226000"},
            {"date": "2026-09-03", "close": "228000"},
        ]

        def timeline_for(query, start_date, end_date):
            if query == builder.intervention_query():
                key = "intervention"
            else:
                key = next(name for name, q in builder.factor_queries().items() if q == query)
            out = {}
            for day, values in fixture.items():
                point = values[key]
                out[day] = builder.normalize_timeline_entry(point["value"], point["norm"])
            return out

        original = builder.fetch_timeline
        builder.fetch_timeline = timeline_for
        try:
            result = builder.build(prices, sleep_seconds=0, news_lag_days=1)
        finally:
            builder.fetch_timeline = original

        self.assertEqual(result[0]["war"], "1.00000000")
        self.assertEqual(result[0]["sanctions"], "0.50000000")
        self.assertEqual(result[0]["currency"], "0.15000000")
        self.assertEqual(result[1]["war"], "0.60000000")
        self.assertEqual(result[1]["currency"], "0.20000000")

    def test_fixture_can_be_materialized_as_enriched_csv(self):
        fixture_path = Path(__file__).parent.parent / "data" / "experimental" / "gdelt_timeline_fixture.json"
        with fixture_path.open("r", encoding="utf-8") as fh:
            fixture = json.load(fh)

        prices = [{"date": day, "close": "220000"} for day in fixture]

        def timeline_for(query, start_date, end_date):
            if query == builder.intervention_query():
                key = "intervention"
            else:
                key = next(name for name, q in builder.factor_queries().items() if q == query)
            return {
                day: builder.normalize_timeline_entry(values[key]["value"], values[key]["norm"])
                for day, values in fixture.items()
            }

        original = builder.fetch_timeline
        builder.fetch_timeline = timeline_for
        try:
            result = builder.build(prices, sleep_seconds=0, news_lag_days=0)
        finally:
            builder.fetch_timeline = original

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "enriched.csv"
            builder.write_csv(result, path)
            with path.open("r", encoding="utf-8", newline="") as fh:
                rows = list(csv.DictReader(fh))

        self.assertEqual(len(rows), 3)
        self.assertEqual(set(rows[0]), {"date", "close", *builder.FACTORS})
        self.assertEqual(rows[2]["currency"], "0.12500000")


if __name__ == "__main__":
    unittest.main()
