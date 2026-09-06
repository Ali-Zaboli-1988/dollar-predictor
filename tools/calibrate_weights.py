#!/usr/bin/env python3
"""Walk-forward calibration for Dollar Predictor factor weights.

CSV columns required:
  close,war,sanctions,oil,diplomacy,currency,economy

Rows must be chronological (oldest -> newest). Factor columns are the
point-in-time scores available at each observation and must not contain
information from the future.

The calibrator searches a small, deliberately bounded grid of integer
multipliers. It optimizes directional accuracy on walk-forward samples,
then reports coverage and the selected weights. This is a calibration aid,
not a claim of statistical significance.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import math
from dataclasses import dataclass
from pathlib import Path

FACTORS = ("war", "sanctions", "oil", "diplomacy", "currency", "economy")

@dataclass(frozen=True)
class Row:
    close: float
    factors: tuple[float, ...]

@dataclass(frozen=True)
class Metrics:
    samples: int
    hits: int
    accuracy: float
    coverage: float


def load_rows(path: Path) -> list[Row]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        required = {"close", *FACTORS}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            missing = sorted(required - set(reader.fieldnames or []))
            raise ValueError("CSV missing columns: " + ", ".join(missing))
        rows: list[Row] = []
        for raw in reader:
            try:
                close = float((raw.get("close") or "").replace(",", ""))
                values = tuple(float(raw.get(name, "0") or "0") for name in FACTORS)
            except ValueError:
                continue
            if close > 0 and math.isfinite(close) and all(math.isfinite(v) for v in values):
                rows.append(Row(close, values))
    if len(rows) < 20:
        raise ValueError("At least 20 valid observations are required")
    return rows


def evaluate(rows: list[Row], weights: tuple[int, ...], threshold: float, min_move: float) -> Metrics:
    opportunities = max(0, len(rows) - 1)
    samples = hits = 0
    for i in range(opportunities):
        score = sum(value * weight for value, weight in zip(rows[i].factors, weights))
        predicted = 1 if score > threshold else -1 if score < -threshold else 0
        actual_move = (rows[i + 1].close - rows[i].close) / rows[i].close
        actual = 1 if actual_move > min_move else -1 if actual_move < -min_move else 0
        if predicted == 0 or actual == 0:
            continue
        samples += 1
        hits += int(predicted == actual)
    accuracy = 100.0 * hits / samples if samples else 0.0
    coverage = 100.0 * samples / opportunities if opportunities else 0.0
    return Metrics(samples, hits, accuracy, coverage)


def walk_forward_calibration(
    rows: list[Row],
    candidate_values: tuple[int, ...],
    train_size: int,
    test_size: int,
    threshold: float,
    min_move: float,
) -> tuple[int, ...]:
    if len(rows) <= train_size + test_size:
        raise ValueError("Not enough observations for walk-forward calibration")

    votes = {weights: 0.0 for weights in itertools.product(candidate_values, repeat=len(FACTORS))}
    start = train_size
    while start < len(rows) - 1:
        train_end = min(start, len(rows) - 1)
        test_end = min(start + test_size, len(rows))
        training = rows[:train_end]
        best_weights = None
        best_key = None
        for weights in votes:
            metrics = evaluate(training, weights, threshold, min_move)
            if metrics.samples < 8:
                continue
            # Prefer accuracy, then coverage, then smaller absolute weights.
            key = (
                metrics.accuracy,
                metrics.coverage,
                -sum(abs(w) for w in weights),
            )
            if best_key is None or key > best_key:
                best_key = key
                best_weights = weights
        if best_weights is not None:
            test_rows = rows[:test_end]
            test_metrics = evaluate(test_rows, best_weights, threshold, min_move)
            if test_metrics.samples:
                votes[best_weights] += test_metrics.accuracy / 100.0
        start += test_size
    return max(votes, key=votes.get)


def main() -> int:
    parser = argparse.ArgumentParser(description="Walk-forward factor weight calibrator")
    parser.add_argument("csv", type=Path)
    parser.add_argument("--train-size", type=int, default=20)
    parser.add_argument("--test-size", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=1.0)
    parser.add_argument("--min-move", type=float, default=0.003)
    parser.add_argument("--min-weight", type=int, default=0)
    parser.add_argument("--max-weight", type=int, default=2)
    args = parser.parse_args()
    if args.train_size < 10 or args.test_size < 1:
        raise SystemExit("train-size must be >= 10 and test-size must be >= 1")
    if args.min_weight > args.max_weight:
        raise SystemExit("min-weight must not exceed max-weight")

    rows = load_rows(args.csv)
    values = tuple(range(args.min_weight, args.max_weight + 1))
    weights = walk_forward_calibration(rows, values, args.train_size, args.test_size, args.threshold, args.min_move)
    baseline = tuple(1 for _ in FACTORS)
    chosen_metrics = evaluate(rows, weights, args.threshold, args.min_move)
    baseline_metrics = evaluate(rows, baseline, args.threshold, args.min_move)

    print("factors=" + ",".join(FACTORS))
    print("selected_weights=" + ",".join(str(v) for v in weights))
    print(f"selected_accuracy={chosen_metrics.accuracy:.2f}%")
    print(f"selected_coverage={chosen_metrics.coverage:.2f}%")
    print(f"baseline_accuracy={baseline_metrics.accuracy:.2f}%")
    print(f"baseline_coverage={baseline_metrics.coverage:.2f}%")
    print("note=Weights must be validated out-of-sample before being copied into the Android model.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
