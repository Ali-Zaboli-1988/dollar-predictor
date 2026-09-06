#!/usr/bin/env python3
"""Fetch historical USD/IRR closes from TGJU's table-data endpoint."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import math
import time
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE_URL = "https://api.tgju.org/v1/market/indicator/summary-table-data/{slug}"
SLUG = "price_dollar_rl"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "en-US,en;q=0.5",
    "Origin": "https://www.tgju.org",
    "Referer": "https://www.tgju.org/",
}


def build_params(length: int) -> list[tuple[str, str]]:
    if length < 1:
        raise ValueError("length must be positive")
    params: list[tuple[str, str]] = [("lang", "fa"), ("order_dir", "asc"), ("draw", "2")]
    for i in range(9):
        params.extend(
            [
                (f"columns[{i}][data]", str(i)),
                (f"columns[{i}][name]", ""),
                (f"columns[{i}][searchable]", "true"),
                (f"columns[{i}][orderable]", "true"),
                (f"columns[{i}][search][value]", ""),
                (f"columns[{i}][search][regex]", "false"),
            ]
        )
    params.extend(
        [
            ("start", "0"),
            ("length", str(length)),
            ("search", ""),
            ("order_col", ""),
            ("order_dir", ""),
            ("from", ""),
            ("to", ""),
            ("convert_to_ad", "1"),
            ("_", str(int(time.time() * 1000))),
        ]
    )
    return params


def fetch_raw(length: int, timeout: int = 30) -> dict:
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
    text = str(value).strip().replace(",", "").replace("٬", "")
    if not text or text in {"-", "—"}:
        return None
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
            continue
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
    print("source=TGJU")
    print(f"rows={len(rows)}")
    print(f"first_date={rows[0]['date']}")
    print(f"last_date={rows[-1]['date']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
