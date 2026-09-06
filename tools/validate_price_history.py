#!/usr/bin/env python3
"""Validate a fetched TGJU USD/IRR price history before modeling."""

from __future__ import annotations

import argparse
import csv
from datetime import date
from pathlib import Path


MAX_DAILY_MOVE_PCT = 25.0


def load_rows(path: Path) -> list[tuple[date, int]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["date", "close"]:
            raise ValueError(f"unexpected columns: {reader.fieldnames!r}")

        rows: list[tuple[date, int]] = []
        for line_no, row in enumerate(reader, start=2):
            try:
                day = date.fromisoformat(row["date"].strip())
                close = int(row["close"].strip())
            except Exception as exc:
                raise ValueError(f"invalid row {line_no}: {row!r}") from exc
            if close < 10_000 or close > 10_000_000:
                raise ValueError(f"close out of range at row {line_no}: {close}")
            rows.append((day, close))
    return rows


def validate(path: Path, minimum_rows: int) -> tuple[int, date, date, float]:
    rows = load_rows(path)
    if len(rows) < minimum_rows:
        raise ValueError(f"only {len(rows)} rows; minimum is {minimum_rows}")

    dates = [day for day, _ in rows]
    if len(set(dates)) != len(dates):
        raise ValueError("duplicate dates found")
    if dates != sorted(dates):
        raise ValueError("dates are not in ascending order")

    largest_move = 0.0
    for (_, previous), (_, current) in zip(rows, rows[1:]):
        move_pct = abs((current - previous) / previous) * 100.0
        largest_move = max(largest_move, move_pct)
        if move_pct > MAX_DAILY_MOVE_PCT:
            raise ValueError(
                f"implausible daily move {move_pct:.2f}% exceeds {MAX_DAILY_MOVE_PCT:.2f}%"
            )

    return len(rows), dates[0], dates[-1], largest_move


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--minimum-rows", type=int, default=60)
    args = parser.parse_args()

    count, first_day, last_day, largest_move = validate(args.path, args.minimum_rows)
    print(f"rows={count}")
    print(f"first_date={first_day.isoformat()}")
    print(f"last_date={last_day.isoformat()}")
    print(f"largest_abs_move_pct={largest_move:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
