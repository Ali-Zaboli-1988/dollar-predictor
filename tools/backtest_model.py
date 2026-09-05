#!/usr/bin/env python3
"""Offline walk-forward evaluator for Dollar Predictor trend signals.

CSV input must contain a chronological `close` column ordered oldest -> newest.
The evaluator never uses future observations when generating a signal.

Example:
    python tools/backtest_model.py history.csv
"""

from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Metrics:
    samples: int
    hits: int
    accuracy: float
    coverage: float
    avg_abs_move: float


def load_closes(path: Path) -> list[float]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames or "close" not in reader.fieldnames:
            raise ValueError("CSV must contain a close column")
        values: list[float] = []
        for row in reader:
            raw = (row.get("close") or "").strip().replace(",", "")
            if not raw:
                continue
            try:
                value = float(raw)
            except ValueError:
                continue
            if value > 0 and math.isfinite(value):
                values.append(value)
    if len(values) < 12:
        raise ValueError("At least 12 valid close observations are required")
    return values


def predict_direction(history: list[float], lookback: int = 5, threshold: float = 0.003) -> int:
    current = history[-1]
    oldest = history[-1 - lookback]
    trend = (current - oldest) / oldest
    if trend > threshold:
        return 1
    if trend < -threshold:
        return -1
    return 0


def evaluate(closes: list[float], lookback: int = 5, threshold: float = 0.003) -> Metrics:
    opportunities = 0
    samples = 0
    hits = 0
    abs_moves: list[float] = []

    for end in range(lookback, len(closes) - 1):
        history = closes[: end + 1]
        predicted = predict_direction(history, lookback, threshold)
        actual_move = (closes[end + 1] - closes[end]) / closes[end]
        actual = 1 if actual_move > 0 else -1 if actual_move < 0 else 0
        opportunities += 1
        abs_moves.append(abs(actual_move) * 100.0)
        if predicted == 0 or actual == 0:
            continue
        samples += 1
        hits += int(predicted == actual)

    accuracy = 100.0 * hits / samples if samples else 0.0
    coverage = 100.0 * samples / opportunities if opportunities else 0.0
    avg_abs_move = sum(abs_moves) / len(abs_moves) if abs_moves else 0.0
    return Metrics(samples, hits, accuracy, coverage, avg_abs_move)


def calibrate_weight(metrics: Metrics) -> int:
    """Map historical directional accuracy to a deliberately small model weight."""
    if metrics.samples < 8:
        return 0
    if metrics.accuracy >= 65:
        return 3
    if metrics.accuracy >= 58:
        return 2
    if metrics.accuracy >= 52:
        return 1
    if metrics.accuracy <= 35:
        return -3
    if metrics.accuracy <= 42:
        return -2
    if metrics.accuracy <= 48:
        return -1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Walk-forward evaluator for Dollar Predictor")
    parser.add_argument("csv", type=Path)
    parser.add_argument("--lookback", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=0.003)
    args = parser.parse_args()

    if args.lookback < 2:
        raise SystemExit("lookback must be >= 2")
    closes = load_closes(args.csv)
    metrics = evaluate(closes, args.lookback, args.threshold)
    weight = calibrate_weight(metrics)

    print(f"observations={len(closes)}")
    print(f"samples={metrics.samples}")
    print(f"hits={metrics.hits}")
    print(f"accuracy={metrics.accuracy:.2f}%")
    print(f"coverage={metrics.coverage:.2f}%")
    print(f"avg_abs_next_day_move={metrics.avg_abs_move:.3f}%")
    print(f"validation_weight={weight:+d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
