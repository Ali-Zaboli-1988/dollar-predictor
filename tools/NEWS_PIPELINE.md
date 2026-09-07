# Historical News Pipeline

The preferred historical news path is `build_news_features_timeline.py`.

It uses GDELT DOC `TimelineVolRaw` rather than requesting an ArticleList separately for every price date. TimelineVolRaw returns the actual number of matching articles per time interval, so one timeline request can cover the whole historical window. This reduces request volume substantially and is more appropriate for rate-limited historical feature extraction.

For each factor, the pipeline runs one historical timeline query over the full price range. A separate currency-intervention query is used to subtract intervention-related coverage from the currency factor. The resulting daily features remain aligned to the TGJU price dates.

The pipeline is still a feature-engineering and calibration input, not evidence that news causes the price move. Real calibration must remain strict walk-forward and must be kept separate from the Android production weights until the historical evidence is sufficiently large and stable.

The legacy ArticleList builder remains available for short, interactive use and regression coverage, but it is not the preferred path for bulk historical calibration because ArticleList is capped and the API is rate-limited.
