# Reviewer passes, 2026-11-06

These are three adversarial passes carried out by the AI assistant, not by independent human reviewers. They do not satisfy the audit's reviewer gates or replace author sign-off.

## Pass 1: AI novelty

| # | Objection | Severity | Evidence | Resolution |
|---|---|---|---|---|
| N1 | EAAI asks for novel aspects of AI. This study has no new algorithm | **High** | Guide, Aims and scope; `provenance/journal-rule-comparison-2026-11-06.md` | **Blocker for Original Research.** Abstract says the contribution is evaluative. Route to IFAC EAAI Forum or Case Study; author decides |
| N2 | Chance-control and evaluation-first framing is already in Chikane (2026) | High | `novelty/novelty-matrix.csv` | Cited and credited. Remaining difference: supervised models, state-only comparator, all four failures held out, five horizons, calibration, SHAP |
| N3 | Mali et al. already cover supervised multi-horizon evaluation | High | Full text read | Cited; design difference measured |
| N4 | Closest papers read only partly: Hamdi Alaoui (abstract), Toribio (abstract), Guha, Teng and Gao, Shikdar, Kanimozhi and Yao (metadata plus supplied audit) | **High** | Novelty matrix `full_text_access` | **Open.** The gap claim stays scoped to sources searched. Guha, Teng and Gao, Shikdar, Kanimozhi and Yao are not cited for content. Must be read before submission |
| N5 | Scopus and Web of Science not searched | Medium | `novelty/search-log.md` | **Open.** Stated in manuscript; author to run saved strings |
| N6 | Novelty gate overall | High | N1 to N5 | **Unresolved** |

## Pass 2: Empirical validity

| # | Objection | Severity | Evidence | Resolution |
|---|---|---|---|---|
| E1 | Could below-chance AUROC be a bug? | High | Tie bug found and fixed; `logs/sanity.txt` | Tie-corrected, tested, and independently recomputed with `scipy.rankdata` (max difference 0 over 140 cells). Training AUROC 0.99 to 1.00 and model-free signal reversal support the result |
| E2 | The bug was fixed after viewing results | Medium | `provenance/deviations.md` #1 | Disclosed; scores unchanged |
| E3 | Zero catches may reflect a strict alarm rule, not absent signal | **High** | Threshold is the 99.5th percentile plus 3-of-5 persistence | Partly addressed: exploratory oracle thresholds catch 6 of 20 at 2.8 false alarms a day, on two failures only. Claim is worded as "the registered alarms", not "no signal exists" |
| E4 | Model scope is narrow: no tuning and no sequence model | **High** | `provenance/event-study-config.json` | **Open limitation.** Stated in manuscript; claim limited to models tested. A stronger comparator is the most valuable next experiment |
| E5 | Thresholds and calibrator come from cross-fit models but apply to a refit model trained on more data | Medium | `event_study.run_fold` | Design limitation; noted here. Could shift alarm rates |
| E6 | Forward folds train on one failure, giving at most 50 distinct scores | Medium | `tables/primary-metrics.csv` | Reported in text; isolated high AUROC not presented as skill |
| E7 | Signal reversal may reflect season or unreported operating changes | High | `tables/exploratory-single-feature.csv`; July block oil ranks high | Labelled exploratory, unadjusted, no mechanism claimed |
| E8 | Reported start may not be onset, and registered ±1 hour label sensitivity from the draft protocol was NOT run | Medium | Not in frozen plan | **Open.** Not claimed |
| E9 | Random-split demo is not a replication of any published study | High | `provenance/deviations.md` #5 | Manuscript says it does not explain any specific published result |
| E10 | Claim about Mali et al.'s partition depends on UCI labels | High | `results/split_check_output.txt` | Worded conditionally: must rest on other labels or another procedure |
| E11 | Independent rerun | Low | Identical digests on 150 cells; bundled predictions byte-identical to the author's earlier run | Pass, same machine |

## Pass 3: Engineering usefulness

| # | Objection | Severity | Evidence | Resolution |
|---|---|---|---|---|
| U1 | No maintenance engineer set the limits; costs are unmodelled | High | `provenance/registered-plan.md` | Limits labelled provisional; no savings claimed |
| U2 | Burden "pass" is hollow because alarms rarely fired | Medium | `tables/rule-outcomes.csv` | Stated in Results |
| U3 | One compressor and one fault type | High | Data | Stated in abstract and discussion |
| U4 | A practitioner needs a next step | Medium | Discussion | Report episode counts per partition; seek a dataset with more failures. The 2022 MetroPT release has 3 further failures but is unverified as independent, and its 1.6 GB download needs author approval |
| U5 | 5-minute minimum response is not validated | Low | Registered plan | Provisional |

## Outcome

**Evidence-limited draft.** Not ready for author submission review as Original Research. Open before any submission: N1, N4, N5, E4, E8, author metadata, repository deposit, human reviewer sign-off.
