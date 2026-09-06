#!/usr/bin/env python3
"""Build daily news factor features aligned to a historical USD/IRR price CSV.

Input CSV must contain: date,close
Output CSV contains: date,close,war,sanctions,oil,diplomacy,currency,economy

The news source is GDELT DOC 2.0 Article List. GDELT exposes article search over
historical windows and returns publication/seen timestamps that can be aggregated
by UTC date. This tool intentionally keeps feature extraction deterministic so the
result can be walk-forward validated by calibrate_weights.py.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import time
from collections import defaultdict
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

FACTOR_KEYWORDS = {
    "war": (
        "war", "attack", "strike", "missile", "conflict", "escalation",
        "military", "hormuz", "blockade", "iran war"
    ),
    "sanctions": (
        "sanction", "sanctions", "secondary sanctions", "treasury",
        "financial pressure", "maximum pressure"
    ),
    "oil": (
        "oil", "crude", "brent", "wti", "oil export", "oil exports",
        "tanker", "shipping", "strait of hormuz"
    ),
    "diplomacy": (
        "ceasefire", "talks", "negotiation", "negotiations", "agreement",
        "deal", "truce", "de-escalation", "peace"
    ),
    "currency": (
        "central bank", "foreign currency", "fx intervention",
        "currency intervention", "inject", "reserves", "rial", "dollar",
        "currency"
    ),
    "economy": (
        "inflation", "inflationary", "imports", "trade", "economic crisis",
        "economy", "recession", "economic growth"
    ),
}

INTERVENTION_TERMS = ("intervention", "inject", "reserves", "central bank buying")


def parse_date(value: str) -> dt.date:
    return dt.date.fromisoformat(value)


def load_prices(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError("Price CSV is empty")
    required = {"date", "close"}
    missing = sorted(required - set(rows[0]))
    if missing:
        raise ValueError("Price CSV missing columns: " + ", ".join(missing))
    for row in rows:
        parse_date(row["date"])
        float(row["close"])
    return rows


def classify(title: str) -> dict[str, int]:
    text = title.lower()
    scores = {name: 0 for name in FACTOR_KEYWORDS}
    for factor, terms in FACTOR_KEYWORDS.items():
        if any(term in text for term in terms):
            scores[factor] = 1
    if scores["currency"] and any(term in text for term in INTERVENTION_TERMS):
        scores["currency"] = -1
    if scores["diplomacy"]:
        scores["diplomacy"] = -1
    return scores


def day_bounds(day: dt.date) -> tuple[str, str]:
    start = dt.datetime.combine(day, dt.time.min, tzinfo=dt.timezone.utc)
    end = start + dt.timedelta(days=1)
    return start.strftime("%Y%m%d%H%M%S"), end.strftime("%Y%m%d%H%M%S")


def fetch_gdelt(day: dt.date, timeout: int = 30) -> list[str]:
    start, end = day_bounds(day)
    query = '(Iran OR Tehran) (dollar OR rial OR sanctions OR oil OR war OR ceasefire OR negotiation OR economy)'
    params = {
        "query": query,
        "mode": "artlist",
        "maxrecords": "250",
        "sort": "datedesc",
        "format": "json",
        "STARTDATETIME": start,
        "ENDDATETIME": end,
    }
    url = "https://api.gdeltproject.org/api/v2/doc/doc?" + urlencode(params)
    request = Request(url, headers={"User-Agent": "dollar-predictor/1.0"})
    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    articles = payload.get("articles", [])
    return [str(article.get("title", "")) for article in articles if article.get("title")]


def build(prices: list[dict[str, str]], sleep_seconds: float) -> list[dict[str, str]]:
    features: dict[str, dict[str, int]] = {}
    unique_days = sorted({parse_date(row["date"]) for row in prices})
    for index, day in enumerate(unique_days, start=1):
        counts = defaultdict(int)
        try:
            titles = fetch_gdelt(day)
            seen = set()
            for title in titles:
                key = " ".join(title.lower().split())
                if key in seen:
                    continue
                seen.add(key)
                for factor, value in classify(title).items():
                    counts[factor] += value
            features[day.isoformat()] = {name: counts[name] for name in FACTOR_KEYWORDS}
        except Exception as exc:
            raise RuntimeError(f"GDELT fetch failed for {day}: {exc}") from exc
        if sleep_seconds > 0 and index < len(unique_days):
            time.sleep(sleep_seconds)
    output = []
    for row in prices:
        key = parse_date(row["date"]).isoformat()
        item = {"date": key, "close": row["close"]}
        item.update({name: str(features[key][name]) for name in FACTOR_KEYWORDS})
        output.append(item)
    return output


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    fields = ["date", "close", *FACTOR_KEYWORDS]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("prices", type=Path, help="Historical price CSV with date,close columns")
    parser.add_argument("output", type=Path, help="Output training CSV")
    parser.add_argument("--sleep", type=float, default=0.25, help="Delay between GDELT day queries")
    args = parser.parse_args()

    rows = load_prices(args.prices)
    enriched = build(rows, args.sleep)
    write_csv(enriched, args.output)
    print(f"wrote={args.output} rows={len(enriched)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
