# Model Evidence and Validation Boundaries

## Confirmed in CI

- Android debug APK build completed successfully for commit `1fc3e9d4f756c9ea882a98a66ed1c99b59404e84`.
- APK artifact SHA-256: `42cc65dfb301a25c3ac6ce41307ee979655b533cfc75dc53477f948f3ae4815a`.
- Real TGJU fetcher successfully retrieved 75 observations from 2026-06-01 through 2026-09-05 in the real price backtest pipeline.
- The independent real price/regime walk-forward test reported 71.43% out-of-sample accuracy with 63.64% coverage, while the simple baseline reported 73.21% accuracy with 75.68% coverage.

## Interpretation

The recent-window result is useful as a diagnostic, but it does not justify injecting new regime parameters into the Android model because the baseline was slightly stronger and the sample is small.

Calibration tests that use generated fixtures are regression tests for implementation correctness. They are not evidence of live-market predictive accuracy.

The real-news calibration remains blocked by GDELT HTTP 429 rate limiting. The pipeline is manual-only and has retry/backoff handling so that an unavailable external news API does not make normal repository CI misleadingly red.

## Data integrity gate

`tools/validate_price_history.py` validates fetched price histories before they can enter real calibration. It rejects malformed schemas, duplicate dates, descending dates, out-of-range prices, and implausible daily moves above 25%.

This gate is intentionally conservative: a rejected file should be investigated rather than silently repaired for modeling.

## Next evidence threshold

No production model weight should be changed solely from the current 2026-06-01 to 2026-09-05 window. A parameter change should require a stronger out-of-sample advantage over the baseline across a materially larger, point-in-time dataset and across multiple market regimes.
