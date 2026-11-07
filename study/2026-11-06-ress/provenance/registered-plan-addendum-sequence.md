# Registered addendum: sequence models

Frozen 2026-11-07, before any sequence model was scored on real data. Hashes are in `addendum-freeze-hashes.txt`. This is an internal dated freeze added after results for M0 to M4 were known. It is not external preregistration or blinded.

## Why it was added

Reviewers can fairly ask whether stronger temporal models transfer where M1 to M4 did not. Hamdi Alaoui et al. (2026) report an LSTM with ROC-AUC 0.96 on a reduced MetroPT-3 subset, so an LSTM is the direct comparison.

## Disclosure

The results for M0 to M4, including the reversal of signals across failures, were known when these models were specified. No architecture was chosen to fit those results, and no tuning is run. Settings were sized only by run time on synthetic data.

## Models

- **M5, LSTM:** one layer, 32 hidden units, using the final state.
- **M6, temporal convolutional network:** five causal blocks, 32 channels, kernel 3, dilations 1 to 16.
- **Input:** 60 one-minute cells of all 15 channels plus an observed flag; the decision minute itself is excluded. Scaling is fitted on training minutes only. Missing minutes become 0 with the flag set to 0, with no future filling.
- **Training:** 500 AdamW steps, learning rate 0.001, batch 256 with 25% positive decisions, then a prior correction back to the training base rate.
- **Reproducibility:** CPU, fixed seeds, one seed per fit, fixed thread count.

## Evaluation

Identical to the registered plan: the same labels, valid decisions, folds A to E, 13-hour embargo, cross-fitted Platt calibration, 99.5th-percentile thresholds on calibration-role negatives, 3-of-5 persistence, 60-minute merging, 5-minute minimum lead and 1,000 circular shifts. Metrics use the tie-correct functions from the start.

## Pre-specified interpretation

- **Primary comparison:** M5 and M6 versus M1 and M3, per held-out failure and horizon.
- **Decision rules:** the first five rules of the registered plan apply unchanged. The explanation rule is not assessed because SHAP is not run for M5 and M6.
- **Calibration gate:** unchanged, so calibration stays exploratory and per failure, and supports no risk claim.
- **If a sequence model passes at some horizon:** the manuscript must say so and the non-transfer conclusion must be narrowed.
- **If none passes:** the claim extends only to these two small architectures, not to all sequence models.

## Exploratory, labelled in advance

M5 on a row-random 60/40 split at each horizon, to show the split effect for an LSTM. It is not an estimate of warning ability and not a replication of any published study.

## Known limit

Architectures are deliberately small and untuned. One seed is used per fit, so seed variation is not measured for M5 and M6.
