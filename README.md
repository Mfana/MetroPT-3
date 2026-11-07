# MetroPT-3 whole-failure validation

Analysis code, frozen settings, saved prediction scores and derived tables for "Do early-warning models transfer between failures? Whole-failure validation of statistical, tree and sequence models on a metro train compressor" (Ngwenya, under review).

Results describe one compressor and four reported air leaks, and support no risk claim.

## Layout

- `study/2026-11-06-ress/README.md`: how the study is organised and the order to run its scripts
- `study/2026-11-06-ress/extensions/`: analysis code and tests
- `study/2026-11-06-ress/provenance/`: registered plan, addenda, frozen settings, freeze hashes and deviations
- `study/2026-11-06-ress/runs/`: saved scores and run records, including reruns
- `study/2026-11-06-ress/tables/`: derived tables
- `study/2026-11-06-ress/submission-ress/`: claim ledger and figure data
- `study/2026-11-06-ress/novelty/`: literature matrix and search log
- `data/raw/README.md`: where to get the raw file

Run scripts from `study/2026-11-06-ress` using the packages in `requirements.txt` on Python 3.13.

## Not included

- The raw CSV, which UCI hosts.
- The manuscript and title page, so `extensions/check_claims_ress.py` and the `patch_*` and `build_*` scripts cannot run from this repository alone. The claim ledger holds their result.
- Database exports with abstracts, and journal rule notes.
- The bundled runner behind `runs/bundled-default` and `runs/bundled-rerun`. Its outputs are included.

Local paths in logs and shell scripts were replaced with `<repo>`. `MANIFEST.sha256` lists a digest for every file here.

## Licence

- **Code:** MIT (`LICENSE`). This covers `scripts/` and `study/2026-11-06-ress/extensions/`, including shell scripts in `study/2026-11-06-ress/logs/`.
- **Everything else:** CC BY 4.0 (`LICENSE-CC-BY-4.0.txt`). This covers tables, scores, run records, logs, figure data, plans, settings and notes.
- **Source data:** the scores and tables derive from the MetroPT-3 dataset by Davari, Veloso, Ribeiro and Gama, UCI Machine Learning Repository, DOI 10.24432/C5VW3R, CC BY 4.0. Please credit it as well.

## Folder name

The study folder was named `2026-11-06-eaai` until 2026-11-07, when it was renamed for the RESS target. Run records in `runs/` and `provenance/plan-freeze-hashes.txt` keep the old path, because they record what was run at the time. Nothing else changed in them.
