import datetime as dt
import unittest
from unittest.mock import patch

import build_news_features_timeline as builder


class NewsTimelineFeatureTests(unittest.TestCase):
    def test_factor_queries_cover_all_factors(self):
        queries = builder.factor_queries()
        self.assertEqual(set(queries), set(builder.FACTORS))
        self.assertTrue(all("Iran" in query for query in queries.values()))

    @patch("build_news_features_timeline.urlopen")
    def test_fetch_timeline_parses_daily_values(self, urlopen_mock):
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
                        {"date": "20260901000000", "value": 12},
                        {"date": "20260902000000", "value": 7},
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
        self.assertEqual(result, {"2026-09-01": 12, "2026-09-02": 7})

    @patch("build_news_features_timeline.fetch_timeline")
    def test_build_uses_one_timeline_per_factor_plus_intervention(self, fetch_mock):
        def fake(query, start_date, end_date):
            if "intervention" in query or "inject" in query or "reserves" in query:
                return {"2026-09-01": 3}
            return {"2026-09-01": 10}

        fetch_mock.side_effect = fake
        prices = [{"date": "2026-09-01", "close": "227205"}]
        result = builder.build(prices, sleep_seconds=0)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["war"], "10")
        self.assertEqual(result[0]["currency"], "7")
        self.assertEqual(fetch_mock.call_count, len(builder.FACTORS) + 1)


if __name__ == "__main__":
    unittest.main()
