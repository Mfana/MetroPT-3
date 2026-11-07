# Registered analysis plan

Frozen 2026-11-06, before this study's held-out scoring. Hashes are in `plan-freeze-hashes.txt`. This is an internal dated freeze, not an external preregistration.

## Disclosure of earlier access

This is not blinded or prospective. Failure dates are public. Before this freeze, the author's feasibility runs (`Research Plan/metropt-eaai-results`) scored the anomaly models on 15 Jul, 29 May and 5 Jun, and the assistant inspected state-conditioned sensor means and failure-window load shares. Supervised models M1 to M4 had not been fitted or scored on any failure before this freeze.

## Author decisions

1. Default gates stay: 5 positive episodes for calibration, 10 for intervals. Four reports fail both.
2. Calibration on MetroPT-3 is exploratory and per failure. It supports no risk claim.
3. The downloaded CSV in `data/raw/` is used through an existing-file path, an authorized exception to keep-raw-off-disk. The runner saves no raw rows.

## Question and estimands

Primary question: at each warning horizon, does supervised sensor information add value beyond an operating-state-only model on a whole failure it has not seen?

- Primary comparison: M3 versus M1, per held-out failure and horizon, on window average precision and Brier skill score against the training-fold base rate.
- Secondary: M3 versus M2 (non-linearity), M3 versus M4 (state conditioning), and the bundled anomaly scorers from the frozen default run.
- Event evidence: catches per failure, with lead at least 5 minutes, false alarms per scored day and a circular-shift chance rate (1,000 shifts), the control used by Chikane (2026).
- Explanations: SHAP stability of M3 across seeds, horizons and failures, on the same 30-minute pre-failure rows.

## Fixed settings

No hyperparameter tuning occurs; all settings are fixed in `event-study-config.json`. Horizons are 30 minutes and 1, 3, 6 and 12 hours. One decision per minute uses a causal 60-minute lookback. Negatives are decimated 5 to 1 in training with base-rate-preserving weights. Alarms need 3 of 5 consecutive decisions above the 0.995 quantile of calibration-role negative margins, with 60-minute merging.

## Folds

| Analysis | Train | Calibration role | Test |
|---|---|---|---|
| A | Other 3 blocks | Cross-fitted | Each block |
| B | Other episodes | Cross-fitted | {apr18}, {may29, jun05}, {jul15} |
| C | apr18 block | may29 block | jun05 block |
| D | apr18 block | may29 and jun05 blocks | jul15 block |
| E | Blocks 1 to 3 | Cross-fitted | From 16 Jul maintenance, false alarms only |

Embargo is 13 hours each side of a block boundary. Failures and recovery are excluded: reported maintenance for jun05 and jul15; a fixed 24 hours for apr18 and may29, because one report is absent and one date is unreliable.

## Pre-specified interpretation

A horizon is defensible only if all of these hold, and otherwise the result is reported as not supported.

| Rule | Limit |
|---|---|
| Beats the base rate | Platt-calibrated Brier skill above 0 in all 4 analysis A failures |
| Beats operating state | M3 above M1 in both AP and Brier skill in at least 3 of 4 analysis A failures, and in analysis D |
| Slope | Calibration slope 0.7 to 1.3 in at least 3 of 4 |
| Warning | At least 3 of 4 caught, with a chance rate below 0.5 for each counted catch |
| Burden | At most 1 false alarm per scored day in analysis A median and analysis E |
| Explanations | Median cross-horizon and cross-failure top-5 overlap not below the 10th percentile of cross-seed overlap |

These numeric limits are author-unconfirmed defaults, so the outcome is labelled provisional. A horizon passing the rules is still not a risk claim, because the calibration gate fails.

Beating M1 is not the sole test of usefulness: an air leak can raise compressor duty, so state features may carry true degradation signal. M1 skill therefore means "explainable from duty and cycling", not "spurious".

## Known limits

One compressor, four air-leak reports, public dates, non-independent windows. No significance tests are run. Numbers are descriptive.
