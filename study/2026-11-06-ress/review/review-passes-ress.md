# Reviewer passes for the RESS manuscript, 2026-11-07

These are adversarial passes carried out by the AI assistant, not by independent human reviewers. They do not replace author sign-off.

## Pass 1: fit and novelty

| # | Objection | Severity | Evidence | Resolution |
|---|---|---|---|---|
| R1 | RESS may read this as a machine-learning benchmark critique on one unit, not a reliability contribution | **High** | Abstract; aims of RESS; Basora 2025 and Vieira 2026 are precedents only by analogy | **Open.** Framed around warning, alarm burden and reporting practice. The RESS scope names automatic fault detection and diagnosis, test and maintenance policies, and data collection and analysis, and accepts industrial case studies. DCE is the agreed fallback. Author judgement needed |
| R2 | No new method; the principle (grouped validation) is known, and Marmoucha 2026 already reports near-zero recall on one chronological test failure | High | Related work | Stated openly. The added value is holding out every failure at five horizons, the joint test, the state and chance controls, the label-timing result and the rank-score shift control |
| R3 | Table 1 and related work rest on partial reading: Guha about half plus targeted passages, Teng first 55%, Toribio abstract and passages | **High** | `novelty/novelty-matrix.csv` | **Closed 2026-11-07.** All three read to the conclusions; caption changed; Toribio added to Table 1. Guha's tables other than Table 8, and Teng's tables, are not in the extracted text |
| R4 | Scopus and Web of Science not searched, so the gap claim may be wrong | **High** | `novelty/search-log.md` | **Closed 2026-11-07.** Six searches run in each database through the author's login; gap statement holds at abstract level. Marmoucha 2026 and Kulkarni 2026 added. Lead-time papers (Chakri, Alhammadi, Silva) were then read in full; see R21 |
| R5 | Mali 2026 printed DOI does not resolve and the journal is minor | Medium | Memory note; bib uses URL | Cited for positioning only, by URL |

## Pass 2: empirical validity

| # | Objection | Severity | Evidence | Resolution |
|---|---|---|---|---|
| R6 | M5 and M6 were added after M0 to M4 results were known | High | Addendum | Disclosed in text; no tuning; rules unchanged |
| R7 | 500 steps and one seed may underfit, so the negative result may be about training | **High** | Random-split M5 AUROC 0.90 to 0.99 shows learning; no held-in AUROC measured for M5 and M6 | **Mostly closed 2026-11-07.** Median training AUROC 0.96 to 1.00, above the 0.90 limit at every horizon; five seeds run: 3 of 280 further tests caught, none meets the rules. Larger setting dropped before it ran (deviation 10), so models remain small and untuned |
| R8 | The alarm threshold may be what fails, not the model: M5 was silent in 15 of 20 cells | High | `tables/seq-metrics.csv`; oracle check for M3 only | **Closed 2026-11-07.** At the 95th percentile M5 and M6 each catch 5 of 20, all on 29 May or 5 June, so the threshold is not the whole explanation |
| R9 | The rank shift control was post hoc and could be chosen to weaken the good result | **High** | Deviation 8 | Disclosed as exploratory, applied to all models and cells, and it also flags a low-tail excess. Not used in any rule |
| R10 | Shifted windows may land on other unreported degradation, so they are not pure chance | Medium | Limitations | Stated as "arbitrary period", not as a null of no signal |
| R11 | Grouped-fold drop on 29 May could simply reflect pooling two events | Medium | Results | Stated in the same sentence |
| R12 | Label timing sensitivity (±1 hour) never run | Medium | Limitations | **Closed for shared shifts 2026-11-07.** -60: 0 of 145. +60: 32 of 145, which is detection: 15 of 16 alarms at 3 h and above fired after the reported start. No horizon passes. Independent per-failure errors untested |
| R13 | Rounding errors in earlier draft | Low | Deviation 9 | Fixed; 38 numbers now recomputed against the text by `extensions/check_claims_ress.py` |

| R17 | The +60 result could be read as showing the models do warn and that reports are late | **High** | Figure 3; `tables/gaps-shift-plus60-alarm-timing.csv` | Addressed in Discussion: sustained loaded runs begin 15, 11 and 5 min before and 23 min after the reported start, and alarms follow. A longer reporting lag cannot be excluded from this data alone, and an engineer's reading would help |
| R18 | The 18 April report has only a date, so ±60 min may not span its error | Medium | `provenance/event-study-events.csv` | Stated in Limitations. Its run starts 23 min after midnight, which suggests the date is meaningful but does not prove it |
| R19 | Seed catches: why treat them as not warning? | High | Results | All three are reported with lead, chance rate and burden. Two fall inside the sustained run. The third, 157 min before 5 June, has 4.08 false alarms a day |
| R20 | Toribio et al. evaluate against 16 air-leak intervals, 12 beyond the company reports. This study counts those 12 as normal time, so training labels may be noisy and false alarms overstated, and with 16 events the calibration gates (5 and 10) might no longer be failed | **High** | `provenance/toribio2026-table1-intervals.csv`; `logs/extra-intervals-check.txt`: 11 of 12 coincide with a sustained loaded run; 11 of 26 away runs of 30 min or more fall on them (rotated median 0, share at least observed 0.001) | **Mostly closed 2026-11-07 by addendum 3, on saved scores.** 4 of 354 caught against about 7.1 expected; 0 of 30 reach the warning share; removed time holds 5.8% of time and 2.3% of false alarms; burden outcomes unchanged. **Still open:** models were trained with these intervals as normal, and Davari et al. 2021 is unread, so a model trained on all 16, and the gate question, remain untested |
| R21 | Published lead times of 17 min to 5.4 h appear to contradict no warning | High | Full texts; `tables/onset-load-share.csv` | **Addressed.** Definitions differ: Chakri credits flags inside the failure; Alhammadi's two hours is one failure and false positives in its metrics; Silva uses the 2022 release and the LPS signal. **Open:** 15 July looks unusual in two papers and in this data (48% loaded against a median of 10%). One event cannot separate precursor, reporting lag or heavy use. An engineer's reading would help |
| R22 | Catches use the unmerged signal while burden uses notifications; denominator includes time with no valid decision (outside review) | **High** | `tables/alarm-def-rules.csv` | **Closed by addendum 4.** New alerts: 0 of 250, 3 of 280, 32 to 29. Decision share 96.7%; no burden flips |
| R23 | 250 evaluations read as more evidence than four failures (outside review) | High | Abstract; Results | **Closed.** Four failures lead the abstract, highlight and conclusions; 50 forward-only tests stated separately; forward tests rest on one training failure |
| R24 | Platt and onset claims went beyond what was measured (outside review) | High | Methods; Discussion | **Closed.** Nonnegative constraint stated; $b$ separated from slope; 25-minute claim removed |
| R25 | Decision rules not explained for maintainers (outside review) | Medium | Pre-specified interpretation | **Partly closed.** Plain-language text added. The limits still have no engineer's rationale |
| R26 | Second outside review: alarm wording, timing contradiction, feasibility claim, unsupported 0.50 reference | High | Code; `tables/alarm-boundary.csv` | **Closed.** Rule wording matches code; 31 of 32 stated; feasibility narrowed to this study's thresholds; 0.50 reported descriptively; plan-versus-code boundary disclosed (3 to 6 of 280) |

## Pass 3: engineering usefulness

| # | Objection | Severity | Evidence | Resolution |
|---|---|---|---|---|
| R14 | No maintenance engineer set limits, and no costs are modelled | High | Pre-specified section | Stated; no savings claimed. Consider asking an engineer to review limits |
| R15 | Reporting list is advice drawn from one case | Medium | Section 6.2 | Worded as "our results support", limited to rare-failure data |
| R16 | Practitioners want to know what would work | Medium | Further work | Points to independent failures and physical features, unproven |

## Outcome

**Evidence-limited draft, reshaped for RESS.** Not ready for submission until R1 (author judgement), author metadata, repository deposit and human sign-off are settled. R7, R8 and R12 were addressed by addendum 2 on 2026-11-07. The remaining empirical limits are small untuned models, shared rather than independent timing shifts, and the same-machine reruns.
