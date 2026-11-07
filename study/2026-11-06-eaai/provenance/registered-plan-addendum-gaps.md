# Registered addendum 2: closing sequence-model gaps

Frozen 2026-11-07, before any fit below was scored. Hashes are in `addendum-gaps-freeze-hashes.txt`. This is an internal dated freeze, not external preregistration, and it is not blind: every M0 to M6 result was known when it was written. Its purpose is to answer review objections R7, R8 and R12 in `review/review-passes-ress.md`. A timing pilot on real training rows recorded seconds only and computed no metric.

Nothing here changes the frozen results of the registered plan or addendum 1. Everything here is a sensitivity analysis and is reported as such. Results are reported whichever way they fall.

## 1. Training fit (held-in) check

Refit M5 and M6 in analysis A, at all five horizons, with the frozen settings, seed and thread count. Score the training rows and the held-out block. The held-out digest must equal the frozen digest in `runs/seq-study/run.json`; this proves the check describes the same model. Report AUROC and AP on all training decisions, and AUROC within each training failure's own block.

Interpretation fixed in advance, per model and horizon, using median pooled training AUROC across the four folds:

- At least 0.90: underfitting is not the main explanation of the held-out result.
- Below 0.80: the negative result may reflect underfitting, and the manuscript must say so.
- Otherwise: mixed, and reported as mixed.

## 2. Best-case threshold

Apply the existing `rescore.oracle_policy` to saved M5 and M6 analysis A scores at q = 0.90, 0.95, 0.98 and 0.99, exactly as was done for M1 to M4. The threshold uses the test block's own negatives, so this is an optimistic upper bound and not part of any rule.

## 3. Seed variation

Four further seeds (1791, 2791, 3791, 4791), giving five with the frozen 791. Folds: A, D, E and `B_hold_may29_jun05`. All five horizons, M5 and M6, full pipeline. Apply the same five rules as addendum 1 per seed, with the frozen M1 as comparator. Report the range of AUROC across seeds per cell, total catches, and the 29 May result alone and with 5 June. Apply the circular label-shift control to every analysis A cell of each seed, by the method of `extensions/rank_chance.py`.

If any seed and horizon passes all five rules, the manuscript must say so and narrow the non-transfer conclusion. A one-seed reproduction check repeats `A_holdjul15` for seed 1791.

## 4. Larger models

M5 and M6 with 64 hidden units or channels and 2,000 steps, seed 791, analysis A, all five horizons, full pipeline, plus the same held-in check. This is one pre-specified larger setting. It is **not tuning**: nothing is selected, and tuning remains undone. Folds D and E are run only if some horizon meets the Brier, slope and warning rules in analysis A, since a horizon that fails those cannot pass.

## 5. Label timing

Move all four reported onsets together by 60 minutes earlier and by 60 minutes later. Reported ends are unchanged. Labels, exclusions, blocks, thresholds and catch windows all follow the moved onset, and everything is refit.

- M5 and M6: folds A, D and E, all five horizons, seed 791.
- M1 to M4: `event_study.py` unchanged, analysis A and folds D and E with the models registered for those folds. SHAP is off and folds B and C are not run.

Apply the same five rules with M1 refit under the same shift as comparator. Moving all onsets together does not cover independent errors per failure. The 18 April report carries a date only, so ±60 minutes does not span its real uncertainty.

## Not addressed

No hyperparameter search. No model family beyond LSTM and TCN. Independent per-failure timing errors. No new failure data.
