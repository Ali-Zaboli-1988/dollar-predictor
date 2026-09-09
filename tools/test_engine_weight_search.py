#!/usr/bin/env python3
"""Regression tests for leakage-safe engine weight search."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.engine_weight_search import Row, validation_score


def test_validation_score_uses_only_past_rows() -> None:
    rows = [Row(str(i), 100.0 + i * 0.8) for i in range(20)]
    cutoff = 12
    baseline = validation_score(rows, cutoff)

    # Change only observations at/after the prediction cutoff. A historical
    # validation score must be invariant to those future values.
    future_changed = rows[:cutoff] + [
        Row(str(i), 100000.0 - i * 1000.0) for i in range(cutoff, len(rows))
    ]
    assert validation_score(future_changed, cutoff) == baseline


def test_validation_score_handles_prediction_near_end_without_index_error() -> None:
    rows = [Row(str(i), 100.0 + i * 0.5) for i in range(10)]
    validation_score(rows, 8)


if __name__ == "__main__":
    test_validation_score_uses_only_past_rows()
    test_validation_score_handles_prediction_near_end_without_index_error()
    print("engine_weight_search_tests=PASS")
