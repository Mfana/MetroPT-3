# MetroPT-3 study, 2026-11-06 (target changed from EAAI to RESS, DCE fallback)

**Outcome: evidence-limited draft.** No warning horizon met the pre-specified rules, and calibration on four failures supports no risk claim.

Across M1 to M6, registered alarms caught 0 of 250 failure tests.


## Reproduce

Run from the project root. Python 3.13 with NumPy and SciPy is needed; the default `python3` on this machine is 3.8 and too old.

```sh
S=study/2026-11-06-ress; CSV="data/raw/MetroPT3(AirCompressor).csv"
(cd $S/extensions && python3.13 -B -m unittest test_event_study test_rescore)
python3.13 -B .claude/skills/metropt-eaai/scripts/run.py --existing-csv "$CSV" --config $S/provenance/study-frozen-draft.json --events $S/provenance/uci-events.csv --out NEW_DIR_A
python3.13 -B $S/extensions/event_study.py --csv "$CSV" --config $S/provenance/event-study-config.json --events $S/provenance/event-study-events.csv --out NEW_DIR_B
```

Sequence models need PyTorch in the project `.venv` (`provenance/seq-requirements.txt`). `logs/run_seq.sh` runs the study and rerun.

From inside `study/2026-11-06-ress`, using `../../.venv/bin/python`, in this order: `extensions/seq_tables.py`, `extensions/rank_chance.py`, `extensions/build_ress.py`, `extensions/check_claims_ress.py`, then `extensions/ress_audit.py submission-ress` after compiling.

Earlier tables are rebuilt from inside `study/2026-11-06-ress` with `extensions/rescore.py`, `leakage_demo.py`, `sanity.py` and `build_tables.py`.

## Layout

| Path | Contents |
|---|---|
| `provenance/` | Registered plan, deviations, frozen settings, hashes, journal rule comparison |
| `novelty/` | Search logs, novelty matrix, reference verification |
| `runs/` | Bundled and event-study runs, with reruns |
| `tables/` | Cite `primary-metrics.csv`, not the uncorrected rank metrics in `run.json` |
| `review/` | Assistant reviewer passes for EAAI and RESS |
| `submission-ress/` | RESS staging folder, claim ledger, RESS audit output |

## Addendum 2 (2026-11-07): sensitivity analyses

Plan: `provenance/registered-plan-addendum-gaps.md`; hashes: `provenance/addendum-gaps-freeze-hashes.txt`. Run with `logs/run_gaps.sh` (resumes finished tasks; outputs in `runs/gaps/`), then, from this folder, `extensions/gaps_oracle.py`, `extensions/gaps_tables.py`, `extensions/gaps_onset.py`, `extensions/build_gaps_ress.py` and `extensions/check_claims_ress.py`. Results are in `tables/gaps-*.csv`. Larger-model phases were dropped before running (deviation 10).

## Literature update, 2026-11-07

After `extensions/build_gaps_ress.py`, run `extensions/patch_literature_ress.py`, then `extensions/check_claims_ress.py`. Published values are in `provenance/literature-extracts-2026-11-07.csv`; Toribio et al.'s intervals are in `provenance/toribio2026-table1-intervals.csv`. `extensions/extra_intervals_check.py` is read-only (log: `logs/extra-intervals-check.txt`).

## Addendum 3, 2026-11-07

Plan: `provenance/registered-plan-addendum-intervals.md`; hashes: `provenance/addendum-intervals-freeze-hashes.txt`. From this folder run `extensions/extra16.py`, `extensions/extra16_tables.py`, `extensions/patch_extra16_ress.py` (after `patch_literature_ress.py`) and `extensions/check_claims_ress.py`. Results are in `tables/extra16-*.csv`; logs in `logs/extra16.txt` and `logs/extra16-tables.txt`. Nothing is refitted.

## Search and full-text updates, 2026-11-07

After `patch_extra16_ress.py`, run `extensions/patch_search_ress.py`, `extensions/onset_load_share.py`, `extensions/patch_fulltext_ress.py`, then `extensions/check_claims_ress.py`.

Last manuscript patch: `extensions/patch_sciencedirect_ress.py`, run after `patch_fulltext_ress.py` and before `check_claims_ress.py`.

Author postal address was entered directly in `submission-ress/manuscript.tex` and `title-page.tex` on 2026-11-07. Re-running the build scripts would need it re-entered.

Outside review, 2026-11-07: plan `provenance/registered-plan-addendum-alarm-defs.md`; run `extensions/alarm_defs.py`, then `extensions/patch_review_ress.py` after `patch_sciencedirect_ress.py`, then `extensions/check_claims_ress.py`. The postal address is entered by hand afterwards.

Second review: run `extensions/alarm_boundary.py`, then `extensions/patch_review2_ress.py` after `patch_review_ress.py`, then `extensions/check_claims_ress.py`.
