#!/usr/bin/env python3
"""Walk-forward backtest for the price/trend component used by the Android app."""
from __future__ import annotations

import argparse
import csv
import itertools
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Row:
    date: str
    close: float


@dataclass(frozen=True)
class Metrics:
    samples: int
    hits: int
    opportunities: int

    @property
    def accuracy(self) -> float:
        return 100.0 * self.hits / self.samples if self.samples else 0.0

    @property
    def coverage(self) -> float:
        return 100.0 * self.samples / self.opportunities if self.opportunities else 0.0


def load_rows(path: Path) -> list[Row]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames or not {"date", "close"}.issubset(reader.fieldnames):
            raise ValueError("CSV must contain date,close")
        rows = [Row(r["date"], float(r["close"].replace(",", ""))) for r in reader]
    rows.sort(key=lambda r: r.date)
    if len(rows) < 25:
        raise ValueError("At least 25 price observations are required")
    return rows


def pct(newer: float, older: float) -> float:
    return ((newer - older) / older) * 100.0


def predict(rows: list[Row], index: int, lookback: int, threshold_pct: float) -> int:
    if index < lookback:
        return 0
    trend = pct(rows[index].close, rows[index - lookback].close)
    if trend >= threshold_pct:
        return 1
    if trend <= -threshold_pct:
        return -1
    return 0


def evaluate(rows: list[Row], lookback: int, threshold_pct: float, min_move: float) -> Metrics:
    opportunities = len(rows) - 1
    samples = hits = 0
    for i in range(opportunities):
        predicted = predict(rows, i, lookback, threshold_pct)
        actual = pct(rows[i + 1].close, rows[i].close) / 100.0
        direction = 1 if actual > min_move else -1 if actual < -min_move else 0
        if predicted == 0 or direction == 0:
            continue
        samples += 1
        hits += int(predicted == direction)
    return Metrics(samples, hits, opportunities)


def walk_forward(rows: list[Row], train_size: int, test_size: int, min_move: float) -> tuple[int, float, float, float]:
    candidates = list(itertools.product((3, 5, 7, 10), (0.5, 0.75, 1.0, 1.5)))
    total = Metrics(0, 0, 0)
    selected_history: list[tuple[int, float]] = []

    start = train_size
    while start < len(rows) - 1:
        test_end = min(start + test_size, len(rows) - 1)
        ranked = []
        for lookback, threshold in candidates:
            train = rows[:start]
            m = evaluate(train, lookback, threshold, min_move)
            if m.samples < 5:
                continue
            ranked.append((m.accuracy, m.coverage, -lookback, -threshold, lookback, threshold))
        if ranked:
            ranked.sort(reverse=True)
            lookback, threshold = ranked[0][4], ranked[0][5]
            block = Metrics(0, 0, test_end - start)
            samples = hits = 0
            for i in range(start, test_end):
                predicted = predict(rows, i, lookback, threshold)
                actual = pct(rows[i + 1].close, rows[i].close) / 100.0
                direction = 1 if actual > min_move else -1 if actual < -min_move else 0
                if predicted == 0 or direction == 0:
                    continue
                samples += 1
                hits += int(predicted == direction)
            block = Metrics(samples, hits, test_end - start)
            total = Metrics(total.samples + block.samples, total.hits + block.hits, total.opportunities + block.opportunities)
            selected_history.append((lookback, threshold))
        else:
            total = Metrics(total.samples, total.hits, total.opportunities + (test_end - start))
        start += test_size

    if not selected_history:
        return 0, 0.0, 0.0, 0.0
    last_lookback, last_threshold = selected_history[-1]
    return last_lookback, last_threshold, total.accuracy, total.coverage


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--train-size", type=int, default=30)
    parser.add_argument("--test-size", type=int, default=7)
    parser.add_argument("--min-move", type=float, default=0.003)
    args = parser.parse_args()

    rows = load_rows(args.csv)
    lookback, threshold, accuracy, coverage = walk_forward(rows, args.train_size, args.test_size, args.min_move)

    baseline = evaluate(rows, 5, 0.3, args.min_move)
    print(f"rows={len(rows)}")
    print(f"first_date={rows[0].date}")
    print(f"last_date={rows[-1].date}")
    print(f"walk_forward_last_lookback={lookback}")
    print(f"walk_forward_last_threshold_pct={threshold:.2f}")
    print(f"walk_forward_oos_accuracy={accuracy:.2f}%")
    print(f"walk_forward_oos_coverage={coverage:.2f}%")
    print(f"baseline_accuracy={baseline.accuracy:.2f}%")
    print(f"baseline_coverage={baseline.coverage:.2f}%")
    print("note=Small recent window; this evaluates the price/trend component only, not news prediction.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
