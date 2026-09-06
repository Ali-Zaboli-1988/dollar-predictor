import unittest
from unittest.mock import patch

import fetch_tgju_history as fetcher


class TgjuFetcherTests(unittest.TestCase):
    def test_extract_rows_uses_close_and_gregorian_date(self):
        payload = {
            "data": [
                ["1,000", "900", "1,100", "1,050", "1,050", "10", "1%", "2026/09/05", "1405/06/14"],
                ["950", "900", "1,000", "980", "980", "-", "-", "2026/09/04", "1405/06/13"],
            ]
        }
        self.assertEqual(
            fetcher.extract_rows(payload),
            [
                {"date": "2026-09-04", "close": "980"},
                {"date": "2026-09-05", "close": "1050"},
            ],
        )

    def test_extract_rows_deduplicates_dates(self):
        payload = {
            "data": [
                ["", "", "", "", "1,000", "", "", "2026/09/05", ""],
                ["", "", "", "", "1,050", "", "", "2026/09/05", ""],
            ]
        }
        rows = fetcher.extract_rows(payload)
        self.assertEqual(rows, [{"date": "2026-09-05", "close": "1050"}])

    @patch("fetch_tgju_history.urlopen")
    def test_fetch_raw_sends_length(self, urlopen_mock):
        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b"{}"

        urlopen_mock.return_value = Response()
        with patch("fetch_tgju_history.json.load", return_value={"data": []}):
            fetcher.fetch_raw(123)
        request = urlopen_mock.call_args.args[0]
        self.assertIn("length=123", request.full_url)
        self.assertEqual(request.headers["Referer"], "https://www.tgju.org/")


if __name__ == "__main__":
    unittest.main()
