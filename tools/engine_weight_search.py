#!/usr/bin/env python3
"""Leakage-safe weight search for the deterministic price/regime engine.

News is intentionally excluded because the repository does not yet contain a
point-in-time historical news feature set. Each fold selects weights using only
past observations, then evaluates exactly that selected candidate on the next
unseen block. No future test block is used to rank candidates.
"""
from __future__ import annotations

import argparse
import csv
import itertools
import math
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Row:
    date: str
    close: float


@dataclass(frozen=True)
class Candidate:
    trend: float
    volatility: float
    validation: float
    regime: float


@dataclass
class Metrics:
    samples: int = 0
    hits: int = 0
    opportunities: int = 0

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
    if len(rows) < 30:
        raise ValueError("At least 30 observations are required")
    return rows


def pct(newer: float, older: float) -> float:
    return ((newer - older) / older) * 100.0 if older else 0.0


def trend_score(rows: list[Row], i: int) -> int:
    if i < 1:
        return 0
    lb = min(10, i)
    t = pct(rows[i].close, rows[i - lb].close)
    if t >= 5:
        return 4
    if t >= 2:
        return 2
    if t >= 0.75:
        return 1
    if t <= -5:
        return -4
    if t <= -2:
        return -2
    if t <= -0.75:
        return -1
    return 0


def volatility(rows: list[Row], i: int) -> float:
    start = max(1, i - 10)
    moves = [pct(rows[j].close, rows[j - 1].close) for j in range(start, i + 1)
             if rows[j].close > 0 and rows[j - 1].close > 0]
    return math.sqrt(sum(x * x for x in moves) / len(moves)) if moves else 0.0


def volatility_score(rows: list[Row], i: int) -> int:
    v = volatility(rows, i)
    return 2 if v >= 3 else 1 if v >= 1.5 else 0


def regime_score(rows: list[Row], i: int) -> int:
    if i < 5:
        return 0
    short = pct(rows[i].close, rows[i - min(3, i)].close)
    long = pct(rows[i].close, rows[i - min(10, i)].close)
    vol = volatility(rows, i)
    severe = 0
    shock = 0
    for j in range(max(1, i - 10), i + 1):
        move = abs(pct(rows[j].close, rows[j - 1].close))
        severe += move >= 4
        shock += move >= 2.5
    direction = 1 if short > 0.5 else -1 if short < -0.5 else 0
    if severe >= 1 or shock >= 2:
        return direction * 3
    if vol >= 3:
        return direction
    if abs(short) >= 1.5 or abs(long) >= 3:
        return direction * 2
    return 0


def validation_score(rows: list[Row], i: int) -> int:
    """Score historical directional validation using rows strictly before i.

    For a prediction made at index i, every validation sample must have its
    trend window and its next-day outcome fully contained in rows[0:i]. This
    prevents the validation component from reading the current/future row.
    """
    if i < 8:
        return 0
    samples = hits = 0
    lb = min(5, i - 1)

    # Historical transition j -> j+1 must finish before i.  The trend used
    # for that transition is measured from j-lb to j, so j starts at lb.
    for j in range(lb, i - 1):
        current = rows[j].close
        old = rows[j - lb].close
        nxt = rows[j + 1].close
        if min(current, old, nxt) <= 0:
            continue
        move = (current - old) / old
        pred = 1 if move > 0.003 else -1 if move < -0.003 else 0
        actual = 1 if nxt > current else -1 if nxt < current else 0
        if pred and actual:
            samples += 1
            hits += int(pred == actual)

    if samples < 5:
        return 0
    acc = 100 * hits / samples
    if acc >= 65:
        return 3
    if acc >= 58:
        return 2
    if acc >= 52:
        return 1
    if acc <= 35:
        return -3
    if acc <= 42:
        return -2
    if acc <= 48:
        return -1
    return 0


def predict(rows: list[Row], i: int, c: Candidate) -> int:
    score = (
        c.trend * trend_score(rows, i)
        + c.volatility * volatility_score(rows, i)
        + c.validation * validation_score(rows, i)
        + c.regime * regime_score(rows, i)
    )
    if score >= 8:
        return 1
    if score <= -8:
        return -1
    return 0


def evaluate(rows: list[Row], start: int, end: int, c: Candidate) -> Metrics:
    m = Metrics(opportunities=max(0, end - start))
    for i in range(start, end):
        pred = predict(rows, i, c)
        actual = 1 if rows[i + 1].close > rows[i].close else -1 if rows[i + 1].close < rows[i].close else 0
        if pred == 0 or actual == 0:
            continue
        m.samples += 1
        m.hits += int(pred == actual)
    return m


def select_candidate(rows: list[Row], candidates: list[Candidate], end: int) -> Candidate | None:
    ranked: list[tuple[float, float, int, Candidate]] = []
    for c in candidates:
        train = evaluate(rows, 10, end, c)
        if train.samples < 5:
            continue
        ranked.append((train.accuracy, train.coverage, train.samples, c))
    if not ranked:
        return None
    ranked.sort(key=lambda x: (x[0], x[1], x[2], -x[3].trend, -x[3].volatility, -x[3].validation, -x[3].regime), reverse=True)
    return ranked[0][3]


def search(rows: list[Row], train_size: int, test_size: int) -> tuple[Metrics, dict[Candidate, Metrics], list[tuple[int, int, Candidate]]]:
    values = (0.5, 0.75, 1.0, 1.25, 1.5, 2.0)
    candidates = [Candidate(*x) for x in itertools.product(values, repeat=4)]
    selected_metrics: dict[Candidate, Metrics] = {}
    selections: list[tuple[int, int, Candidate]] = []
    aggregate = Metrics()
    start = train_size
    while start < len(rows) - 1:
        end = min(start + test_size, len(rows) - 1)
        chosen = select_candidate(rows, candidates, start)
        if chosen is not None:
            block = evaluate(rows, start, end, chosen)
            aggregate.samples += block.samples
            aggregate.hits += block.hits
            aggregate.opportunities += block.opportunities
            metric = selected_metrics.setdefault(chosen, Metrics())
            metric.samples += block.samples
            metric.hits += block.hits
            metric.opportunities += block.opportunities
            selections.append((start, end, chosen))
        start = end
    return aggregate, selected_metrics, selections


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("csv", type=Path)
    ap.add_argument("--train-size", type=int, default=30)
    ap.add_argument("--test-size", type=int, default=7)
    ap.add_argument("--top", type=int, default=10)
    args = ap.parse_args()
    rows = load_rows(args.csv)
    aggregate, selected_metrics, selections = search(rows, args.train_size, args.test_size)

    print(f"rows={len(rows)}")
    print("news_weights=excluded_no_point_in_time_news_dataset")
    print(f"walk_forward_oos_samples={aggregate.samples}")
    print(f"walk_forward_oos_hits={aggregate.hits}")
    print(f"walk_forward_oos_accuracy={aggregate.accuracy:.2f}")
    print(f"walk_forward_oos_coverage={aggregate.coverage:.2f}")
    print(f"folds={len(selections)}")
    print("rank,trend_weight,volatility_weight,validation_weight,regime_weight,selected_folds,oos_samples,oos_hits,oos_accuracy,oos_coverage")
    ranked = sorted(
        selected_metrics.items(),
        key=lambda x: (x[1].samples, x[1].accuracy, x[1].coverage),
        reverse=True,
    )
    for rank, (c, m) in enumerate(ranked[:args.top], 1):
        folds = sum(1 for _, _, selected in selections if selected == c)
        print(f"{rank},{c.trend:g},{c.volatility:g},{c.validation:g},{c.regime:g},{folds},{m.samples},{m.hits},{m.accuracy:.2f},{m.coverage:.2f}")

    print("fold_selection")
    for start, end, c in selections:
        print(f"{start}:{end},{c.trend:g},{c.volatility:g},{c.validation:g},{c.regime:g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
