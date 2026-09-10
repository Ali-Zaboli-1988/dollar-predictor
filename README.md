# Dollar Predictor

Android app for estimating short-term USD/IRR direction using free market data and news signals.

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

## Build

GitHub Actions builds a debug APK automatically on every push. The build workflow runs Android unit tests before assembling the APK, then uploads the APK as a workflow artifact.

## Model policy

Real-market weights are changed only when strict out-of-sample results beat the same-fold production baseline with meaningful coverage. Failed or unavailable external news sources must not be replaced by unverified production weights; experimental fixtures and candidate weights remain explicitly isolated.
