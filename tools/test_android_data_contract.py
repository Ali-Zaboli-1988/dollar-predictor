import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAIN = ROOT / "app/src/main/java/com/alizaboli/dollarpredictor/MainActivity.java"
ENGINE = ROOT / "app/src/main/java/com/alizaboli/dollarpredictor/PredictionEngine.java"
FLAGS = ROOT / "app/src/main/java/com/alizaboli/dollarpredictor/FeatureFlags.java"
MANIFEST = ROOT / "app/src/main/AndroidManifest.xml"


class AndroidDataContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.main = MAIN.read_text(encoding="utf-8")
        cls.engine = ENGINE.read_text(encoding="utf-8")
        cls.flags = FLAGS.read_text(encoding="utf-8")
        cls.manifest = MANIFEST.read_text(encoding="utf-8")

    def test_price_has_two_providers_and_timeouts(self):
        self.assertGreaterEqual(self.main.count("https://www.tgju.org/profile/price_dollar_rl"), 1)
        self.assertGreaterEqual(self.main.count("https://bonbast.com/"), 1)
        self.assertIn("setConnectTimeout(12000)", self.main)
        self.assertIn("setReadTimeout(15000)", self.main)
        self.assertIn("return 0;", self.main)

    def test_history_has_fallback_and_bounded_rows(self):
        self.assertIn("https://english.tgju.org/profile/price_dollar_rl/history", self.main)
        self.assertIn("https://www.tgju.org/profile/price_dollar_rl/charts-data/history", self.main)
        self.assertRegex(self.main, r"closes\.size\(\)\s*<\s*75")
        self.assertIn("if (closes.size() >= 8) return closes;", self.main)

    def test_parsers_normalize_digits_and_reject_invalid_numbers(self):
        self.assertIn("normalizeDigits", self.main)
        self.assertRegex(self.main, r"raw\s*<=\s*0")
        self.assertRegex(self.main, r"value\s*>=\s*10000")
        self.assertRegex(self.main, r"value\s*<=\s*1000000")

    def test_news_is_experimental_and_off_by_default(self):
        self.assertIn("EXPERIMENTAL_NEWS_ENABLED", self.flags)
        self.assertIn("EXPERIMENTAL_NEWS_ENABLED = false", self.flags)
        self.assertIn("FeatureFlags.EXPERIMENTAL_NEWS_ENABLED", self.engine)
        self.assertIn("new NewsStats(0, 0)", self.engine)

    def test_news_is_failure_safe(self):
        self.assertIn("if (news.isEmpty())", self.main)
        self.assertIn("catch (Exception ignored)", self.main)

    def test_manifest_network_permission_and_exported_launcher(self):
        self.assertIn('android.permission.INTERNET', self.manifest)
        self.assertIn('android:name=".MainActivity"', self.manifest)
        self.assertIn('android:exported="true"', self.manifest)
        self.assertIn('android.intent.category.LAUNCHER', self.manifest)


if __name__ == "__main__":
    unittest.main()
