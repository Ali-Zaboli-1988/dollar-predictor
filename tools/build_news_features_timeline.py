#!/usr/bin/env python3
"""Build daily news factor features using GDELT TimelineVolRaw."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

GDELT_URL = "https://api.gdeltproject.org/api/v2/doc/doc"
MAX_RETRIES = 5
FACTORS = {
    "war": ("war", "attack", "strike", "missile", "conflict", "escalation", "military", "hormuz", "blockade"),
    "sanctions": ("sanction", "sanctions", "secondary sanctions", "treasury", "financial pressure", "maximum pressure"),
    "oil": ("oil", "crude", "brent", "wti", "oil export", "oil exports", "tanker", "shipping", "strait of hormuz"),
    "diplomacy": ("ceasefire", "talks", "negotiation", "negotiations", "agreement", "deal", "truce", "de-escalation", "peace"),
    "currency": ("central bank", "foreign currency", "fx intervention", "currency intervention", "inject", "reserves", "rial", "dollar", "currency"),
    "economy": ("inflation", "inflationary", "imports", "trade", "economic crisis", "economy", "recession", "economic growth"),
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


def _retry_delay(error: HTTPError, attempt: int) -> float:
    retry_after = error.headers.get("Retry-After") if error.headers else None
    if retry_after:
        try:
            return max(1.0, min(300.0, float(retry_after)))
        except ValueError:
            pass
    return min(300.0, 15.0 * (2 ** (attempt - 1)))


def fetch_timeline(query: str, start_date: dt.date, end_date: dt.date, timeout: int = 45) -> dict[str, int]:
    start = dt.datetime.combine(start_date, dt.time.min, tzinfo=dt.timezone.utc)
    end = dt.datetime.combine(end_date + dt.timedelta(days=1), dt.time.min, tzinfo=dt.timezone.utc)
    params = {
        "query": query,
        "mode": "timelinevolraw",
        "format": "json",
        "STARTDATETIME": start.strftime("%Y%m%d%H%M%S"),
        "ENDDATETIME": end.strftime("%Y%m%d%H%M%S"),
    }
    url = GDELT_URL + "?" + urlencode(params)
    for attempt in range(1, MAX_RETRIES + 1):
        request = Request(url, headers={"User-Agent": "dollar-predictor/2.0 (+timeline-news-features)", "Accept": "application/json"})
        try:
            with urlopen(request, timeout=timeout) as response:
                payload = json.load(response)
            timeline = payload.get("timeline", [])
            if not timeline:
                return {}
            # One query normally produces one series; if multiple series are returned,
            # use the first series to avoid double-counting the same query result.
            series = timeline[0].get("data", [])
            result: dict[str, int] = {}
            for entry in series:
                raw_date = str(entry.get("date", ""))
                digits = "".join(ch for ch in raw_date if ch.isdigit())
                if len(digits) < 8:
                    continue
                day = f"{digits[:4]}-{digits[4:6]}-{digits[6:8]}"
                try:
                    parse_date(day)
                    value = max(0, int(float(entry.get("value", 0))))
                except (TypeError, ValueError):
                    continue
                result[day] = value
            return result
        except HTTPError as exc:
            if exc.code != 429 or attempt == MAX_RETRIES:
                raise
            time.sleep(_retry_delay(exc, attempt))
    raise RuntimeError("GDELT timeline request exhausted retries")


def factor_queries() -> dict[str, str]:
    context = "(Iran OR Tehran)"
    return {name: f"{context} ({' OR '.join(terms)})" for name, terms in FACTORS.items()}


def intervention_query() -> str:
    return f"(Iran OR Tehran) ({' OR '.join(INTERVENTION_TERMS)}) (currency OR dollar OR rial OR reserves OR central bank)"


def build(prices: list[dict[str, str]], sleep_seconds: float = 1.5) -> list[dict[str, str]]:
    dates = sorted({parse_date(row["date"]) for row in prices})
    if not dates:
        raise ValueError("No price dates")
    start_date, end_date = dates[0], dates[-1]
    features = {day.isoformat(): {name: 0 for name in FACTORS} for day in dates}
    queries = factor_queries()
    for index, (factor, query) in enumerate(queries.items(), start=1):
        timeline = fetch_timeline(query, start_date, end_date)
        for day, value in timeline.items():
            if day in features:
                features[day][factor] = value
        if sleep_seconds > 0 and index < len(queries):
            time.sleep(sleep_seconds)
    intervention = fetch_timeline(intervention_query(), start_date, end_date)
    for day, value in intervention.items():
        if day in features:
            features[day]["currency"] = max(0, features[day]["currency"] - value)
    output = []
    for row in prices:
        day = parse_date(row["date"]).isoformat()
        item = {"date": day, "close": row["close"]}
        item.update({name: str(features[day][name]) for name in FACTORS})
        output.append(item)
    return output


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ["date", "close", *FACTORS]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("prices", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--sleep", type=float, default=1.5)
    args = parser.parse_args()
    rows = load_prices(args.prices)
    enriched = build(rows, args.sleep)
    write_csv(enriched, args.output)
    print(f"wrote={args.output} rows={len(enriched)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
