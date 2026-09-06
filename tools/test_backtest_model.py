#!/usr/bin/env python3
"""Deterministic smoke/regression tests for the offline trend backtester."""

from __future__ import annotations

import math
import tempfile
from pathlib import Path

from backtest_model import calibrate_weight, evaluate, load_closes, predict_direction


def main() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        csv_path = Path(tmp) / "history.csv"
        csv_path.write_text(
            "close\n" + "\n".join(str(v) for v in [100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112]),
            encoding="utf-8",
        )
        closes = load_closes(csv_path)
        assert len(closes) == 13
        assert predict_direction(closes[:8], lookback=5, threshold=0.003) == 1

        metrics = evaluate(closes, lookback=5, threshold=0.003)
        assert metrics.samples == 7
        assert 0.0 <= metrics.accuracy <= 100.0
        assert math.isclose(metrics.coverage, 100.0, rel_tol=0.0, abs_tol=1e-9)
        assert metrics.avg_abs_move > 0.0
        assert calibrate_weight(metrics) == 0

    print("backtest_model regression tests: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
