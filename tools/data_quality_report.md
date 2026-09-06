# Data Quality Gate

The historical USD/IRR CSV is required to contain `date` and `close` columns, unique ISO dates in ascending order, positive closing prices, and no daily move above the configured quality threshold.

This gate is intentionally separate from model accuracy. Passing it means the input series is structurally usable; it does not establish predictive power.
