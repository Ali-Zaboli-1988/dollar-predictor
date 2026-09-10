import datetime as dt
import unittest
from unittest.mock import patch

import build_news_features_timeline as builder


class NewsTimelineFeatureTests(unittest.TestCase):
    def test_factor_queries_cover_all_factors(self):
        queries = builder.factor_queries()
        self.assertEqual(set(queries), set(builder.FACTORS))
        self.assertTrue(all("Iran" in query for query in queries.values()))

    def test_normalize_timeline_entry_uses_total_monitoring_volume(self):
        self.assertAlmostEqual(builder.normalize_timeline_entry(25, 1000), 2.5)
        self.assertEqual(builder.normalize_timeline_entry(25, 0), 0.0)
        self.assertEqual(builder.normalize_timeline_entry("bad", 1000), 0.0)

    @patch("build_news_features_timeline.urlopen")
    def test_fetch_timeline_parses_and_normalizes_daily_values(self, urlopen_mock):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        urlopen_mock.return_value = Response()
        payload = {
            "timeline": [
                {
                    "series": "Volume Intensity",
                    "data": [
                        {"date": "20260901000000", "value": 12, "norm": 600},
                        {"date": "20260902000000", "value": 7, "norm": 700},
                    ],
                }
            ]
        }
        with patch("build_news_features_timeline.json.load", return_value=payload):
            result = builder.fetch_timeline(
                "(Iran OR Tehran) war",
                dt.date(2026, 9, 1),
                dt.date(2026, 9, 2),
            )
        self.assertEqual(result, {"2026-09-01": 2.0, "2026-09-02": 1.0})

    @patch("build_news_features_timeline.fetch_timeline")
    def test_build_uses_one_day_lag_and_intervention_adjustment(self, fetch_mock):
        def fake(query, start_date, end_date):
            if query == builder.intervention_query():
                return {"2026-08-31": 0.5}
            return {"2026-08-31": 2.0}

        fetch_mock.side_effect = fake
        prices = [{"date": "2026-09-01", "close": "227205"}]
        result = builder.build(prices, sleep_seconds=0)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["war"], "2.00000000")
        self.assertEqual(result[0]["currency"], "1.50000000")
        self.assertEqual(fetch_mock.call_count, len(builder.FACTORS) + 1)

    @patch("build_news_features_timeline.fetch_timeline")
    def test_build_can_disable_lag_explicitly(self, fetch_mock):
        def fake(query, start_date, end_date):
            return {"2026-09-01": 3.0}

        fetch_mock.side_effect = fake
        prices = [{"date": "2026-09-01", "close": "227205"}]
        result = builder.build(prices, sleep_seconds=0, news_lag_days=0)
        self.assertEqual(result[0]["war"], "3.00000000")


if __name__ == "__main__":
    unittest.main()
