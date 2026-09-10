#!/usr/bin/env python3
"""Regression tests for leakage-safe engine weight search."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.engine_weight_search import Candidate, Row, search, validation_score


def test_validation_score_uses_only_past_rows() -> None:
    rows = [Row(str(i), 100.0 + i * 0.8) for i in range(20)]
    cutoff = 12
    baseline = validation_score(rows, cutoff)

    future_changed = rows[:cutoff] + [
        Row(str(i), 100000.0 - i * 1000.0) for i in range(cutoff, len(rows))
    ]
    assert validation_score(future_changed, cutoff) == baseline


def test_validation_score_handles_prediction_near_end_without_index_error() -> None:
    rows = [Row(str(i), 100.0 + i * 0.5) for i in range(10)]
    validation_score(rows, 8)


def test_search_reports_baseline_on_exact_selected_folds_and_excludes_volatility_direction() -> None:
    rows = [Row(str(i), 100.0 + ((i % 9) - 4) * 0.8 + i * 0.2) for i in range(45)]
    selected, baseline, metrics, selections = search(rows, train_size=20, test_size=7)

    assert selections
    assert baseline.opportunities == selected.opportunities
    assert baseline.samples >= 0
    assert baseline.hits <= baseline.samples
    assert all(candidate.volatility == 0.0 for _, _, candidate in selections)
    assert any(candidate.trend < 0 or candidate.validation < 0 or candidate.regime < 0 for _, _, candidate in selections)
    assert Candidate(1.0, 0.0, 0.0, 1.0) not in metrics or metrics[Candidate(1.0, 0.0, 0.0, 1.0)].samples >= 0


if __name__ == "__main__":
    test_validation_score_uses_only_past_rows()
    test_validation_score_handles_prediction_near_end_without_index_error()
    test_search_reports_baseline_on_exact_selected_folds_and_excludes_volatility_direction()
    print("engine_weight_search_tests=PASS")
