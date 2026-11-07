# Registered addendum 3: testing against the twelve further intervals

Frozen 2026-11-07, before any alarm or score was compared with these intervals. Hashes are in `addendum-intervals-freeze-hashes.txt`. This is an internal dated freeze, not external preregistration, and it is not blind: all results against the four reports, and the fact that 11 of the 12 intervals coincide with a sustained loaded run (deviation 13), were known when it was written. Its purpose is to answer review objection R20.

Nothing here changes a frozen result. Everything is a sensitivity analysis on saved scores, and it is reported whichever way it falls.

## What this can and cannot show

No model is refitted. Every model was trained with the 12 intervals counted as normal. So this asks whether models trained on the four company reports warn of, or falsely alarm on, the 12 intervals. It does not ask whether a model trained on all 16 could warn. How Davari et al. derived the intervals is unread, so they may depend on the same sensors.

## Inputs

Scores and thresholds of the registered runs at seed 791: `runs/event-study` (M1 to M4) and `runs/seq-study` (M5, M6). Intervals: `provenance/toribio2026-table1-intervals.csv`, rows marked `no`. Report times stay as frozen, including 18 April.

## Gate

The code first rebuilds alarms from saved scores and frozen thresholds, using `event_study.alarm_series` and the frozen labels. For every cell it must reproduce the frozen false-alarm count, catches and leads. Any mismatch is reported, and the analysis stops if it is not explained.

## 1. False-alarm recount

Build labels with `event_study.build_labels` from all 16 intervals, treating the 12 exactly as reports: warning window positive, active period and recovery excluded. Primary: the default 24-hour recovery. Secondary: no recovery. Recompute false alarms per day for each cell.

Report, per model: false alarms and exposure inside and outside the removed time, median false alarms per day before and after, and the burden rule (analysis A median and analysis E both at most 1 per day) before and after, per model and horizon.

## 2. Warning on the 12 intervals

For each of the 12 in a cell's test block, apply the frozen catch rule: a sustained alarm from `start - h` to `start - 5 min`. An interval is unscorable if that window leaves the block, or overlaps the active period of another interval, or a report's active or recovery period. Compute the circular-shift chance rate by the frozen method. Primary: analysis A, all six models, five horizons. Secondary: all registered cells.

Report tests, catches, catches with chance below 0.5 (the frozen validity limit), by model, horizon and interval, with lead and chance rate.

Because 15 of 16 alarms at long horizons followed the start under the +60 shift, for each catch also report whether the alarm came after the start of a sustained loaded run (COMP inactive for at least 30 minutes) that begins within 120 minutes before the interval start.

## 3. Rule outcome under 16 intervals

The frozen warning rule requires three of four failures, or 75%. Here, per model and horizon in analysis A: catches with chance below 0.5, over the four reports and the 12 intervals together, must reach 75% of scorable tests. Combine with the primary burden recount. Brier skill, the M1 comparison and slope are not recomputed, because the calibrators were fitted under four reports.

## 4. Rank and detection, analysis A

AUROC of the saved margin with positives in the warning windows of the 12 intervals, and separately with positives in their active periods; negatives are label 0 under the 16-interval labels. Circular shift of the positive mask over valid minutes, 1,000 offsets, fixed seed. Also count intervals with a sustained alarm during the active period. M1 is the state-only comparison. No significance tests; shares are descriptive and unadjusted.

## Interpretation fixed in advance

- **Burden:** the false-alarm finding changes only if a model and horizon that failed the burden rule passes under the primary recount. It is then reported as dependent on the labels.
- **Warning:** the no-warning finding must be narrowed if any model and horizon meets section 3 together with burden. Otherwise it stands for these models.
- **Partial signal:** if catches with chance below 0.5 before the loaded run begins are at least 10% of primary tests, the manuscript must say that models trained on four reports show some transfer to the further intervals, and a full 16-label refit becomes the priority.
- **Detection:** high active-period AUROC or alarms during the interval, especially for M1, show detection of a loaded state. They do not show warning, and they cannot validate the intervals as failures.
- **Whichever way this falls:** the intervals stay unverified until Davari et al. is read or an engineer confirms them. This does not change the calibration gates: no calibrator is refitted here.
