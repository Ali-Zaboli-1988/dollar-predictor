# Real-data calibration pipeline

## Price source

The calibration workflow fetches the USD/IRR free-market close series from TGJU's history table-data endpoint using the stable market slug `price_dollar_rl` and requests up to 75 observations for the current calibration window.

The endpoint is an implementation detail used by the TGJU history table rather than a versioned public API contract. The fetcher therefore validates the response schema and fails loudly on malformed data.

## News source

Daily news factor features are generated from GDELT DOC Article List queries. The current feature builder is intentionally deterministic and uses only the article titles returned for each historical day.

## Temporal alignment

A row dated `t` contains only features from the defined information window for `t`. The one-step target is the next observed USD/IRR close. The calibration procedure selects weights on an expanding training window and evaluates them only on later test blocks.

## Current calibration limits

The live workflow uses 75 price observations so that the news stage remains within the practical historical search window of GDELT DOC Article List. The model must not interpret this small window as a multi-year backtest.

For a long-horizon research backtest, use archived GDELT datasets or another explicitly point-in-time historical news source and keep the same walk-forward temporal discipline.
