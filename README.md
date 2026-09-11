# Dollar Predictor

Android app for estimating short-term USD/IRR direction using free market data. The production predictor is rule-based; no ML model file is bundled in the APK.

The app is an analytical tool, not a guaranteed price predictor or financial advice.

## Five-stage delivery plan

1. **Reproducible quality gate** — deterministic Android tests, offline experimental news pipeline, and explicit separation between experimental and production data/models.
2. **Production data integrity** — hardened price/news ingestion, freshness checks, schema validation, and safe fallbacks when external providers fail.
3. **Model validation** — expanding walk-forward OOS evaluation with same-fold baseline comparison, coverage tracking, and a separate untouched holdout before any production weight change.
4. **Product hardening** — prediction UX, failure-state handling, range/risk calibration, lifecycle/network safety, and release-build verification.
5. **Release candidate** — reproducible APK build, final smoke tests, artifact/hash verification, and documented acceptance thresholds.

## Stage 1 acceptance criteria

Stage 1 is complete only when all of the following are true:

- Android unit tests pass before APK construction.
- Offline news feature generation is deterministic and tests normalization plus point-in-time lag.
- Experimental news data is isolated under `data/experimental/` and is never consumed by the production Android engine.
- The experimental news CI can run without GDELT network access.
- A production APK is built from a commit whose Android tests passed.

## Predictor type: rule-based

The production predictor is **rule-based, not ML-based**. It contains no `.tflite`, `.onnx`, `.bin`, `.pkl`, or other trained-model artifact. The Android APK therefore has no separate model payload to load.

Production rules are:

- 10-observation price trend: `>= +5% => +4`, `>= +2% => +2`, `>= +0.75% => +1`; symmetric negative thresholds produce `-4/-2/-1`.
- Trend validation: a 5-observation directional backtest contributes `+3/+2/+1/0/-1/-2/-3` according to measured accuracy bands; it is a validation adjustment, not a trained model.
- Market regime adjustment: TRENDING adds `2` in the trend direction, VOLATILE adds `1`, SHOCK adds `3`; CALM adds `0`.
- Risk/confidence are deterministic functions of score, history size, validation accuracy, volatility, and regime.
- Experimental news keyword scoring exists in code but is behind `FeatureFlags.EXPERIMENTAL_NEWS_ENABLED=false` by default. With the flag off, news contributes zero directional score.

### News decision

News remains **experimental and feature-flagged, OFF by default**. The decision is locked because the real-market OOS comparison was `58.70%` (`27/46`, coverage `16.79%`) versus the same-fold production baseline `65.71%` (`23/35`, coverage `12.77%`): **-7.02 percentage points** in accuracy. That is not evidence for a production weight change. Experimental news must beat the same-fold baseline OOS before the flag can be enabled for production.

## Build

GitHub Actions builds a debug APK automatically on every push. The build workflow runs Android unit tests before assembling the APK, then uploads the APK as a workflow artifact.

## Stage 2 data integrity

Price ingestion uses TGJU with Bonbast fallback, explicit connect/read timeouts, bounded historical rows, digit normalization, numeric/range checks, and safe empty-data handling. Android data-contract tests verify these invariants.

## Model policy

Real-market weights are changed only when strict out-of-sample results beat the same-fold production baseline with meaningful coverage. Failed or unavailable external news sources must not be replaced by unverified production weights; experimental fixtures and candidate weights remain explicitly isolated.
