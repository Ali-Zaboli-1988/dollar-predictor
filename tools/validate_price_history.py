#!/usr/bin/env python3
"""Validate a fetched TGJU USD/IRR price history before modeling."""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from datetime import date
from pathlib import Path


MAX_DAILY_MOVE_PCT = 25.0


@dataclass(frozen=True)
class ValidationResult:
    rows: int
    first_date: date
    last_date: date
    largest_abs_move_pct: float


def load_rows(path: str | Path) -> list[tuple[date, int]]:
    path = Path(path)
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["date", "close"]:
            raise ValueError(f"unexpected columns: {reader.fieldnames!r}")

        rows: list[tuple[date, int]] = []
        for line_no, row in enumerate(reader, start=2):
            try:
                day = date.fromisoformat(row["date"].strip())
                raw_close = float(row["close"].strip().replace(",", ""))
            except Exception as exc:
                raise ValueError(f"invalid row {line_no}: {row!r}") from exc

            if not math.isfinite(raw_close) or not raw_close.is_integer():
                raise ValueError(f"close must be a finite integer at row {line_no}: {row!r}")
            close = int(raw_close)
            if close < 10_000 or close > 10_000_000:
                raise ValueError(f"close out of range at row {line_no}: {close}")
            rows.append((day, close))
    return rows


def validate(
    path: str | Path,
    minimum_rows: int,
    max_daily_change_pct: float = MAX_DAILY_MOVE_PCT,
) -> ValidationResult:
    if minimum_rows < 1:
        raise ValueError("minimum_rows must be positive")
    if max_daily_change_pct <= 0:
        raise ValueError("max_daily_change_pct must be positive")

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
        if move_pct > max_daily_change_pct:
            raise ValueError(
                f"implausible daily move {move_pct:.2f}% exceeds {max_daily_change_pct:.2f}%"
            )

    return ValidationResult(
        rows=len(rows),
        first_date=dates[0],
        last_date=dates[-1],
        largest_abs_move_pct=largest_move,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path)
    parser.add_argument("--minimum-rows", type=int, default=60)
    parser.add_argument("--max-daily-change-pct", type=float, default=MAX_DAILY_MOVE_PCT)
    args = parser.parse_args()

    result = validate(
        args.path,
        args.minimum_rows,
        args.max_daily_change_pct,
    )
    print(f"rows={result.rows}")
    print(f"first_date={result.first_date.isoformat()}")
    print(f"last_date={result.last_date.isoformat()}")
    print(f"largest_abs_move_pct={result.largest_abs_move_pct:.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
