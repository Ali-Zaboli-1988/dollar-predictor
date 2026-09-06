#!/usr/bin/env python3
"""Fetch historical USD/IRR closes from TGJU's table-data endpoint.

The endpoint is used by the TGJU history table and is not treated as a stable,
official public API contract. The script fails loudly on schema changes so a
calibration job cannot silently train on malformed data.

Current TGJU row schema:
  0=open, 1=low, 2=high, 3=close, 4=change, 5=change%, 6=date, 7=jdate
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.tgju.org/v1/market/indicator/summary-table-data/{slug}"
SLUG = "price_dollar_rl"
HEADERS = {
    "User-Agent": "dollar-predictor/1.0",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Referer": "https://www.tgju.org/",
    "Origin": "https://www.tgju.org",
}


def build_params(length: int) -> dict[str, str]:
    return {
        "lang": "fa",
        "draw": "2",
        "start": "0",
        "length": str(length),
        "search": "",
        "order_col": "",
        "order_dir": "asc",
        "from": "",
        "to": "",
        "convert_to_ad": "1",
    }


def fetch_raw(length: int, timeout: int = 30) -> dict:
    if length < 1:
        raise ValueError("length must be positive")
    url = BASE_URL.format(slug=SLUG) + "?" + urlencode(build_params(length))
    request = Request(url, headers=HEADERS)
    with urlopen(request, timeout=timeout) as response:
        payload = json.load(response)
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise ValueError("TGJU response missing data list")
    return payload


def clean_number(value: object) -> float | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text or text in {"-", "—"}:
        return None
    text = text.replace(",", "").replace("٬", "")
    try:
        number = float(text)
    except ValueError:
        return None
    if not math.isfinite(number) or number <= 0:
        return None
    return number


def parse_gregorian(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    for fmt in ("%Y/%m/%d", "%Y-%m-%d"):
        try:
            return dt.datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return None


def extract_rows(payload: dict) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    for raw in payload["data"]:
        if not isinstance(raw, (list, tuple)) or len(raw) < 7:
            continue
        close = clean_number(raw[3])
        day = parse_gregorian(raw[6])
        if close is None or day is None:
            continue
        output.append({"date": day, "close": f"{close:g}"})

    dedup = {row["date"]: row for row in output}
    rows = [dedup[key] for key in sorted(dedup)]
    if not rows:
        raise ValueError("TGJU response contained no valid dated closes")
    return rows


def write_csv(rows: list[dict[str, str]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=["date", "close"])
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch TGJU USD/IRR historical closes")
    parser.add_argument("output", type=Path)
    parser.add_argument("--length", type=int, default=5000)
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()

    rows = extract_rows(fetch_raw(args.length, args.timeout))
    write_csv(rows, args.output)
    print(f"source=TGJU")
    print(f"rows={len(rows)}")
    print(f"first_date={rows[0]['date']}")
    print(f"last_date={rows[-1]['date']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
