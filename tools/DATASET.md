# Real-data training dataset

This project separates **market observations** from **news-derived features** so calibration can be reproduced without hidden assumptions.

## Price input

The canonical price CSV is chronological, oldest first:

```csv
date,close
2026-01-02,1495000
2026-01-03,1502000
```

Required fields:

- `date`: ISO calendar date (`YYYY-MM-DD`)
- `close`: positive numeric USD free-market closing price

The calibration tools require at least 20 valid observations and reject non-finite values.

## Enriched training CSV

The factor dataset contains:

```text
date,close,war,sanctions,oil,diplomacy,currency,economy
```

The six factor columns are point-in-time features. They must contain only information that was available at the prediction timestamp.

For the current daily model, a row for day `t` predicts the direction from `t` to `t+1`. Therefore news aggregated for day `t` is usable only when the forecast is explicitly defined as a next-day forecast made after that day's information cutoff.

## Leakage rules

1. Rows must be chronological.
2. No factor may use a future publication timestamp.
3. The target is the next observation, never the current close.
4. Weight selection is expanding-window walk-forward; test blocks remain strictly out of sample.
5. Do not report fixture/synthetic accuracy as real-world model accuracy.
6. Missing news must be represented explicitly rather than silently backfilled from a future day.

## News sources

`build_news_features.py` uses the GDELT DOC Article List API for recent article retrieval. GDELT documents the DOC API as a rolling historical search service with a limited Article List search horizon, so this path is intended for recent/realtime enrichment rather than silently pretending to be a complete multi-year archive.

For long historical windows, use archived GDELT daily datasets and transform them into the same factor schema before calibration. GDELT publishes downloadable historical event data and the GKG provides document-level thematic metadata.

## Provenance requirement

A production training release should retain, outside the minimal model CSV when practical:

- source name and source URL
- publication/observation timestamp
- source record identifier or stable title hash
- extraction version
- feature schema version
- price data source and retrieval date

The minimal CSV is intentionally kept compatible with the existing calibrator.
