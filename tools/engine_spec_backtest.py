#!/usr/bin/env python3
"""Backtest the Android PredictionEngine scoring specification on price-only data.

This intentionally mirrors the deterministic price/regime components of the Android
engine, while keeping news disabled unless an external historical news CSV is supplied.
It is a validation tool, not a claim of live predictive accuracy.
"""
from __future__ import annotations

import argparse
import csv
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Result:
    samples: int
    hits: int
    coverage: float
    accuracy: float


def load_prices(path: Path) -> list[float]:
    rows: list[tuple[str, float]] = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            date = row.get("date", "").strip()
            raw = row.get("close", "").strip()
            if not date or not raw:
                continue
            value = float(raw)
            if value > 100000:
                value /= 10.0
            rows.append((date, value))
    rows.sort()
    if len(rows) < 10:
        raise ValueError("at least 10 price rows are required")
    return [value for _, value in rows]


def trend_score(history: list[float], end: int) -> int:
    lookback = min(10, end)
    current = history[end]
    old = history[end - lookback]
    pct = ((current - old) / old) * 100.0 if old > 0 else 0.0
    if pct >= 5.0:
        return 4
    if pct >= 2.0:
        return 2
    if pct >= 0.75:
        return 1
    if pct <= -5.0:
        return -4
    if pct <= -2.0:
        return -2
    if pct <= -0.75:
        return -1
    return 0


def volatility(history: list[float], end: int) -> float:
    start = max(0, end - 10)
    moves = []
    for i in range(start + 1, end + 1):
        prev = history[i - 1]
        now = history[i]
        if prev > 0 and now > 0:
            moves.append(((now - prev) / prev) * 100.0)
    return math.sqrt(sum(x * x for x in moves) / len(moves)) if moves else 0.0


def regime_adjustment(history: list[float], end: int) -> tuple[int, str]:
    if end < 5:
        return 0, "CALM"
    short_lb = min(3, end)
    long_lb = min(10, end)
    current = history[end]
    short_old = history[end - short_lb]
    long_old = history[end - long_lb]
    short_pct = ((current - short_old) / short_old) * 100.0 if short_old > 0 else 0.0
    long_pct = ((current - long_old) / long_old) * 100.0 if long_old > 0 else 0.0
    vol = volatility(history, end)
    severe = 0
    shock = 0
    start = max(1, end - 10)
    for i in range(start, end + 1):
        prev = history[i - 1]
        now = history[i]
        if prev <= 0 or now <= 0:
            continue
        move = abs((now - prev) / prev) * 100.0
        severe += move >= 4.0
        shock += move >= 2.5
    if severe >= 1 or shock >= 2:
        return (3 if short_pct > 0.5 else -3 if short_pct < -0.5 else 0), "SHOCK"
    if vol >= 3.0:
        return (1 if short_pct > 0.5 else -1 if short_pct < -0.5 else 0), "VOLATILE"
    if abs(short_pct) >= 1.5 or abs(long_pct) >= 3.0:
        return (2 if short_pct > 0.5 or long_pct > 0.5 else -2), "TRENDING"
    return 0, "CALM"


def predict(history: list[float], end: int, horizon: int) -> int:
    score = trend_score(history, end)
    vol = volatility(history, end)
    score += 2 if vol >= 3.0 else 1 if vol >= 1.5 else 0
    adjustment, _ = regime_adjustment(history, end)
    score += adjustment
    if score >= 8:
        return 1
    if score <= -8:
        return -1
    return 0


def backtest(prices: list[float], horizon: int) -> Result:
    samples = 0
    hits = 0
    evaluated = 0
    for i in range(10, len(prices) - horizon):
        prediction = predict(prices, i, horizon)
        actual_move = prices[i + horizon] - prices[i]
        actual = 1 if actual_move > 0 else -1 if actual_move < 0 else 0
        if actual == 0:
            continue
        evaluated += 1
        if prediction == 0:
            continue
        samples += 1
        if prediction == actual:
            hits += 1
    coverage = 100.0 * samples / evaluated if evaluated else 0.0
    accuracy = 100.0 * hits / samples if samples else 0.0
    return Result(samples, hits, coverage, accuracy)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=Path)
    ap.add_argument("--horizon", type=int, default=1)
    args = ap.parse_args()
    if args.horizon < 1:
        raise SystemExit("--horizon must be positive")
    prices = load_prices(args.csv)
    result = backtest(prices, args.horizon)
    print(f"rows={len(prices)}")
    print(f"horizon={args.horizon}")
    print(f"oos_samples={result.samples}")
    print(f"oos_hits={result.hits}")
    print(f"oos_coverage={result.coverage:.2f}%")
    print(f"oos_accuracy={result.accuracy:.2f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
