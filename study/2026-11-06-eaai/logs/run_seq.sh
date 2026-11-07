#!/bin/zsh
cd <repo>
S=study/2026-11-06-eaai; CSV="data/raw/MetroPT3(AirCompressor).csv"; P=.venv/bin/python
$P -B $S/extensions/seq_study.py --csv "$CSV" --config $S/provenance/seq-config.json --base-config $S/provenance/event-study-config.json --events $S/provenance/event-study-events.csv --out $S/runs/seq-study --workers 3 > $S/logs/seq-study.log 2>&1
$P -B $S/extensions/seq_study.py --csv "$CSV" --config $S/provenance/seq-config.json --base-config $S/provenance/event-study-config.json --events $S/provenance/event-study-events.csv --out $S/runs/seq-rerun-holdjul15 --only-fold A_holdjul15 --workers 3 > $S/logs/seq-rerun.log 2>&1
