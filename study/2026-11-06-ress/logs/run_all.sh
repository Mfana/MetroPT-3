#!/bin/zsh
cd <repo>
S=study/2026-11-06-ress; K=.claude/skills/metropt-eaai; CSV="data/raw/MetroPT3(AirCompressor).csv"
python3.13 -B $K/scripts/run.py --existing-csv "$CSV" --config $S/provenance/study-frozen-draft.json --events $S/provenance/uci-events.csv --out $S/runs/bundled-default > $S/logs/bundled-default.log 2>&1 &
python3.13 -B $K/scripts/run.py --existing-csv "$CSV" --config $S/provenance/study-frozen-draft.json --events $S/provenance/uci-events.csv --out $S/runs/bundled-rerun > $S/logs/bundled-rerun.log 2>&1 &
wait
python3.13 -B $S/extensions/event_study.py --csv "$CSV" --config $S/provenance/event-study-config.json --events $S/provenance/event-study-events.csv --out $S/runs/event-study --workers 7 > $S/logs/event-study.log 2>&1
python3.13 -B $S/extensions/event_study.py --csv "$CSV" --config $S/provenance/event-study-config.json --events $S/provenance/event-study-events.csv --out $S/runs/event-study-rerun --workers 7 > $S/logs/event-study-rerun.log 2>&1
