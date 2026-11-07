# Search log, 2026-11-06

| Index | Query or route | Filter | Result | Artifact |
|---|---|---|---|---|
| Crossref | 5 skill queries in `scripts/novelty.py`, 2 pages of 20 | until 2026-11-06 | 200 records | `crossref.json` |
| OpenAlex | MetroPT-3; MetroPT3; MetroPT air production unit failure prediction; MetroPT calibration probability early warning; air production unit metro compressor multi-horizon calibration SHAP | from 2020-01-01 | 113; 22; 42; 8; 2 | `openalex.json` |
| OpenAlex | Forward citations of the MetroPT dataset paper | from 2026-01-01 | 24 records | `openalex-forward-citations-2026.json` |
| Crossref | 7 targeted queries, including MetroPT plus calibration/Brier | from 2024 or 2025 | First run hit HTTP 429, retried with backoff; no MetroPT calibration paper | console record only |
| Publisher | ScienceDirect guide | n/a | 403 directly; read through author's Chrome | `../provenance/eaai-rule-comparison-2026-11-06.md` |

Limits: Scopus and Web of Science were not searched. Backward tracing covered Mali and Chikane reference lists only. No full-text search of ScienceDirect or EAAI was run. Text search for MetroPT plus calibration cannot detect a paper that calibrates without saying so in title or abstract. The gate is therefore "in the sources searched".

## Full-text reading, 2026-11-07

Read through the author's Chrome: Hamdi Alaoui et al. (full), Guha and Datta (about half plus targeted passages), Teng and Gao (first 55%), Toribio et al. (targeted), Vieira et al. and Basora et al. (abstract and highlights). Still metadata or supplied audit only: Kanimozhi et al., Yao et al., Shikdar and Laaksonen. Scopus and Web of Science remain unsearched.

## Full-text reading completed, 2026-11-07

Read to the end of the conclusions: Teng and Gao (MDPI, open access), Guha and Datta (IEEE Xplore, CC BY; text plus Table 8), Toribio et al. (University of Cordoba repository copy of the CC BY published version, 21 pages). The author's Chrome was not connected; these sources were read in the built-in browser. Davari et al. 2021 has not been read, so how its intervals were derived is unverified.

## Scopus and Web of Science plan, fixed 2026-11-07 before searching

Run through the author's institutional login. Record the date, the exact string, the hit count and the export. Screen every new record against `novelty-matrix.csv`.

| ID | Scopus | Web of Science | Purpose |
|---|---|---|---|
| Q1 | `TITLE-ABS-KEY("MetroPT" OR "MetroPT-3" OR "MetroPT3" OR "Metro PT" OR "Metro do Porto")` | `TS=("MetroPT" OR "MetroPT-3" OR "MetroPT3" OR "Metro PT" OR "Metro do Porto")` | Every study naming the data |
| Q2 | `TITLE-ABS-KEY("air production unit*" AND (metro OR railway* OR train*))` | `TS=("air production unit*" AND (metro OR railway* OR train*))` | Studies describing the unit without the name |
| Q3 | `REF("MetroPT")` | Cited Reference Search for MetroPT in the cited work or title | Studies citing the data without naming it in the abstract |
| Q4 | Q1 or Q2, `AND TITLE-ABS-KEY(calibrat* OR brier OR "reliability diagram" OR "expected calibration error")` | same with `TS=` | Direct test of the gap claim |
| Q5 | Q1 or Q2, `AND TITLE-ABS-KEY(leakage OR "leave-one" OR "hold-out" OR holdout OR "grouped" OR "cross-validation" OR "whole-failure")` | same with `TS=` | Studies on validation design |
| Q6 | `TITLE-ABS-KEY((compressor* OR railway* OR metro) AND ("predictive maintenance" OR "failure prediction" OR "early warning") AND "probability calibration")` | same with `TS=` | The same gap beyond the named dataset |

A database limit or missing feature is recorded, not worked around.

## Scopus results, 2026-11-07

Run in the built-in browser through the author's Unisa login, full access, all years. Exact queries are as Scopus displayed them.

| ID | Hits | Records saved |
|---|---|---|
| Q1 | 64 (many are civil engineering, transport policy or tourism on Metro do Porto) | `scopus-2026-11-07/Q1.json`, with abstracts |
| Q2 | 21 | counted and read in session |
| Q3 | 92 | `scopus-2026-11-07/Q3.json`, with abstracts |
| Q4 | 3: Teng and Gao (thresholds); Chakri et al. 2026 (thresholds); da Fonseca et al. 2010 (geotechnical, not relevant) | counted and read in session |
| Q5 | 8 | counted and read in session |
| Q6 | 1: Dhanuja et al. 2026 (climate and infrastructure, not this problem) | counted and read in session |

## Web of Science results, 2026-11-07

Core Collection, all editions, all years, through the author's login.

| ID | Hits | Notes |
|---|---|---|
| Q1 | 21 | Includes transport-policy papers on Metro do Porto |
| Q2 | 2 | Meira 2023; Marmoucha 2026 |
| Q3 | 4 cited references, one citing article each | Cited Work `MetroPT*`: Coutinho 2026; Alsheikhy 2026; Shawly 2026; Peng 2026. Cited-reference data are sparse, so this is much weaker than Scopus Q3. The See Results control did not appear, so each citing list was opened by its link |
| Q4 | 1 | Teng and Gao (thresholds) |
| Q5 | 3 | Marmoucha 2026; Teng and Gao; Hamdi Alaoui 2026 |
| Q6 | 0 | |

The final query strings are the `TS=` forms in the plan above, with Q4 and Q5 written as `(TS=(Q1 terms) OR TS=(Q2 terms)) AND TS=(...)`.

## Screening, 2026-11-07

Scopus Q1 and Q3 hold 122 unique records. All abstracts were searched for Brier, reliability diagram, expected calibration, probability calibration, Platt, isotonic, leave-one-failure or event, whole-failure, failure-wise, event-wise and per-failure: no hit. All Q2, Q4 and Q6 abstracts were read, Q3 and Q5 titles were read, about 22 further abstracts were read in part, and six candidates were checked further. Web of Science added no new MetroPT evaluation; its extra records are Coutinho 2026 (BIM), Quan 2026 and transport-policy papers. This was not a full dual-reviewer screen and is not a systematic review. Gap statement after search: no MetroPT study found that reports probability calibration across horizons with every failure held out. New close records are in `novelty-matrix.csv`. An IEEE fetch for Kulkarni and Digalwar redirected to Unisa login on the second attempt and was not forced. One IEEE document number was opened by mistake and contained nothing relevant.

## Full text of close papers, 2026-11-07

Read in the built-in browser through the author's Unisa access, in page memory with no file saved: Chakri et al. 2026 (5 pp, full), Alhammadi et al. 2025 (6 pp, full), Silva et al. 2023 (full HTML through Conclusion), Kulkarni and Digalwar 2026 (MetroPT-3 passages of 38 pp). Acar et al. 2026 remains abstract only and is not cited.
