#!/usr/bin/env python3
"""Walk-forward calibration for Dollar Predictor factor weights.

CSV columns required:
  close,war,sanctions,oil,diplomacy,currency,economy

Rows must be chronological (oldest -> newest). Factor columns are the
point-in-time scores available at each observation and must not contain
information from the future.

The calibrator searches a small, deliberately bounded grid of integer
multipliers. It selects weights using expanding-window training and scores
only the subsequent, strictly out-of-sample test block. This is a calibration
aid, not a claim of statistical significance.
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


def predict_from_rows(rows: list[Row], index: int, weights: tuple[int, ...], threshold: float) -> int:
    score = sum(value * weight for value, weight in zip(rows[index].factors, weights))
    if score > threshold:
        return 1
    if score < -threshold:
        return -1
    return 0


def actual_direction(rows: list[Row], index: int, min_move: float) -> int:
    actual_move = (rows[index + 1].close - rows[index].close) / rows[index].close
    if actual_move > min_move:
        return 1
    if actual_move < -min_move:
        return -1
    return 0


def evaluate(rows: list[Row], weights: tuple[int, ...], threshold: float, min_move: float) -> Metrics:
    opportunities = max(0, len(rows) - 1)
    samples = hits = 0
    for i in range(opportunities):
        predicted = predict_from_rows(rows, i, weights, threshold)
        actual = actual_direction(rows, i, min_move)
        if predicted == 0 or actual == 0:
            continue
        samples += 1
        hits += int(predicted == actual)

    accuracy = 100.0 * hits / samples if samples else 0.0
    coverage = 100.0 * samples / opportunities if opportunities else 0.0
    return Metrics(samples, hits, accuracy, coverage)


def evaluate_test_block(
    rows: list[Row],
    start: int,
    end: int,
    weights: tuple[int, ...],
    threshold: float,
    min_move: float,
) -> Metrics:
    """Evaluate only predictions whose decision point lies in [start, end)."""
    if start < 0 or end <= start or end > len(rows) - 1:
        return Metrics(0, 0, 0.0, 0.0)

    opportunities = end - start
    samples = hits = 0
    for i in range(start, end):
        predicted = predict_from_rows(rows, i, weights, threshold)
        actual = actual_direction(rows, i, min_move)
        if predicted == 0 or actual == 0:
            continue
        samples += 1
        hits += int(predicted == actual)

    accuracy = 100.0 * hits / samples if samples else 0.0
    coverage = 100.0 * samples / opportunities if opportunities else 0.0
    return Metrics(samples, hits, accuracy, coverage)


def select_best_weights(
    rows: list[Row],
    candidate_weights: list[tuple[int, ...]],
    threshold: float,
    min_move: float,
) -> tuple[int, ...] | None:
    best_weights = None
    best_key = None

    for weights in candidate_weights:
        metrics = evaluate(rows, weights, threshold, min_move)
        if metrics.samples < 8:
            continue

        key = (metrics.accuracy, metrics.coverage, -sum(abs(w) for w in weights))
        if best_key is None or key > best_key:
            best_key = key
            best_weights = weights

    return best_weights


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

    candidates = list(itertools.product(candidate_values, repeat=len(FACTORS)))
    out_of_sample_scores = {weights: [] for weights in candidates}

    start = train_size
    while start < len(rows) - 1:
        test_end = min(start + test_size, len(rows) - 1)
        best_weights = select_best_weights(rows[:start], candidates, threshold, min_move)
        if best_weights is not None:
            test_metrics = evaluate_test_block(rows, start, test_end, best_weights, threshold, min_move)
            if test_metrics.samples:
                out_of_sample_scores[best_weights].append(
                    (test_metrics.accuracy, test_metrics.coverage, test_metrics.samples)
                )
        start += test_size

    ranked = []
    for weights, blocks in out_of_sample_scores.items():
        if not blocks:
            continue
        total_samples = sum(item[2] for item in blocks)
        weighted_accuracy = sum(item[0] * item[2] for item in blocks) / total_samples
        avg_coverage = sum(item[1] for item in blocks) / len(blocks)
        ranked.append((weighted_accuracy, avg_coverage, -sum(abs(w) for w in weights), weights))

    if not ranked:
        return tuple(1 for _ in FACTORS)

    ranked.sort(reverse=True)
    return ranked[0][3]


def walk_forward_oos_metrics(
    rows: list[Row],
    candidate_values: tuple[int, ...],
    train_size: int,
    test_size: int,
    threshold: float,
    min_move: float,
) -> Metrics:
    """Measure the complete calibration procedure only on unseen test blocks."""
    if len(rows) <= train_size + test_size:
        raise ValueError("Not enough observations for walk-forward evaluation")

    candidates = list(itertools.product(candidate_values, repeat=len(FACTORS)))
    total_opportunities = total_samples = total_hits = 0

    start = train_size
    while start < len(rows) - 1:
        test_end = min(start + test_size, len(rows) - 1)
        best_weights = select_best_weights(rows[:start], candidates, threshold, min_move)
        if best_weights is not None:
            metrics = evaluate_test_block(rows, start, test_end, best_weights, threshold, min_move)
            total_samples += metrics.samples
            total_hits += metrics.hits
        total_opportunities += test_end - start
        start += test_size

    accuracy = 100.0 * total_hits / total_samples if total_samples else 0.0
    coverage = 100.0 * total_samples / total_opportunities if total_opportunities else 0.0
    return Metrics(total_samples, total_hits, accuracy, coverage)


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
    oos = walk_forward_oos_metrics(rows, values, args.train_size, args.test_size, args.threshold, args.min_move)

    baseline = tuple(1 for _ in FACTORS)
    chosen_metrics = evaluate(rows, weights, args.threshold, args.min_move)
    baseline_metrics = evaluate(rows, baseline, args.threshold, args.min_move)

    print("factors=" + ",".join(FACTORS))
    print("selected_weights=" + ",".join(str(v) for v in weights))
    print(f"walk_forward_oos_samples={oos.samples}")
    print(f"walk_forward_oos_accuracy={oos.accuracy:.2f}%")
    print(f"walk_forward_oos_coverage={oos.coverage:.2f}%")
    print(f"descriptive_selected_accuracy={chosen_metrics.accuracy:.2f}%")
    print(f"descriptive_selected_coverage={chosen_metrics.coverage:.2f}%")
    print(f"baseline_accuracy={baseline_metrics.accuracy:.2f}%")
    print(f"baseline_coverage={baseline_metrics.coverage:.2f}%")
    print("note=Only walk-forward OOS metrics should be used as the calibration-performance figure; descriptive metrics use the full dataset.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
