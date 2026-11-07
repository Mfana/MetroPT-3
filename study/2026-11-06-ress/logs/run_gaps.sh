#!/bin/zsh
# Sensitivity phases of provenance/registered-plan-addendum-gaps.md. Finished tasks resume on restart.
cd "$(dirname "$0")/../../.."
S=study/2026-11-06-ress; CSV="data/raw/MetroPT3(AirCompressor).csv"; P=.venv/bin/python; L=$S/logs/gaps
mkdir -p $L
stamp() { echo "$(date +%H:%M:%S) $1" >> $L/progress.txt; }
ev() { local tag=$1
  [ -f $S/runs/gaps/event-$tag/run.json ] && return
  stamp "start event-$tag"; rm -rf $S/runs/gaps/event-$tag
  $P -B -W ignore $S/extensions/event_study.py --csv "$CSV" --config $S/provenance/event-study-config-timing.json --events $S/provenance/events-$tag.csv --out $S/runs/gaps/event-$tag --workers 6 > $L/event-$tag.log 2>&1 || stamp "FAILED event-$tag"; }
sq() { local phase=$1 workers=$2 events=${3:-$S/provenance/event-study-events.csv}
  [ -f $S/runs/gaps/$phase/run.json ] && return
  stamp "start $phase"
  $P -B -W ignore $S/extensions/seq_gaps.py --phase $phase --phases $S/provenance/gaps-phases.json --csv "$CSV" --config $S/provenance/seq-config.json --base-config $S/provenance/event-study-config.json --events $events --out $S/runs/gaps/$phase --workers $workers >> $L/$phase.log 2>&1 || stamp "FAILED $phase"; }
# Larger-model phases dropped by the author's decision before any was run; see provenance/deviations.md item 10.
# Wait for a phase already running when this script was restarted.
while pgrep -f 'seq_gaps.py --phase' > /dev/null; do sleep 30; done
ev minus60; ev plus60
sq heldin 3
for s in 1791 2791 3791 4791; do sq seed$s 6; done
sq seed1791-rerun 6
sq shift-minus60 6 $S/provenance/events-minus60.csv
sq shift-plus60 6 $S/provenance/events-plus60.csv
stamp "all finished"
