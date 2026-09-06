# Data Quality Gate

The historical USD/IRR series must contain `date` and `close`, use unique ISO dates in ascending order, contain positive closes, and remain within the configured daily-move threshold.

Passing this gate only establishes structural data quality. It does not establish model accuracy or predictive power.
