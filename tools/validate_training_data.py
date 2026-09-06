#!/usr/bin/env python3
"""Validate the schema and temporal integrity of a training CSV."""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import math
from pathlib import Path

FACTORS = ("war", "sanctions", "oil", "diplomacy", "currency", "economy")
REQUIRED = ("date", "close", *FACTORS)


def validate(path: Path, minimum_rows: int = 20) -> tuple[int, list[str]]:
    errors: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        fields = tuple(reader.fieldnames or ())
        missing = [name for name in REQUIRED if name not in fields]
        if missing:
            return 0, ["CSV missing columns: " + ", ".join(missing)]

        rows = list(reader)

    if len(rows) < minimum_rows:
        errors.append(f"At least {minimum_rows} rows are required; found {len(rows)}")

    previous_date: dt.date | None = None
    for number, row in enumerate(rows, start=2):
        try:
            day = dt.date.fromisoformat(row["date"])
        except (TypeError, ValueError):
            errors.append(f"row {number}: invalid date")
            continue

        if previous_date is not None and day <= previous_date:
            errors.append(f"row {number}: dates must be strictly increasing")
        previous_date = day

        try:
            close = float((row["close"] or "").replace(",", ""))
            if not (close > 0 and math.isfinite(close)):
                raise ValueError
        except ValueError:
            errors.append(f"row {number}: close must be a positive finite number")

        for factor in FACTORS:
            try:
                value = float(row[factor] or "")
                if not math.isfinite(value):
                    raise ValueError
            except ValueError:
                errors.append(f"row {number}: {factor} must be a finite number")

    return len(rows), errors


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate a Dollar Predictor training CSV")
    parser.add_argument("csv", type=Path)
    parser.add_argument("--minimum-rows", type=int, default=20)
    args = parser.parse_args()

    count, errors = validate(args.csv, args.minimum_rows)
    if errors:
        for error in errors:
            print("ERROR: " + error)
        return 1

    print(f"valid_rows={count}")
    print("schema=ok")
    print("chronology=ok")
    print("numeric_values=ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
