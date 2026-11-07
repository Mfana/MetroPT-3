# Registered addendum 4: alarm definitions and denominators

Frozen 2026-11-07, before any recount below was computed. Hashes are in `addendum-alarm-defs-freeze-hashes.txt`. This is an internal dated freeze, not external preregistration, and it is not blind: all registered and sensitivity results were known. It answers an outside review of the RESS draft.

No model is refitted, and no frozen result changes.

## Issue

`event_study.event_policy` credits a catch from the unmerged persistence signal (`raw`), and counts false alarms from merged notifications (`alarms`). A signal already active when a catch window opens can earn a catch without a new notification. Its denominator is scored minutes (`block & y >= 0`), which includes minutes with no valid lookback, when no decision can be issued.

## Definitions

- **Active signal (registered).** The persistence signal is on at some time in the catch window.
- **New alert (added).** A merged notification starts in the catch window.
- **Per monitored day (registered).** False alarms over scored minutes.
- **Per decision day (added).** False alarms over scored minutes with a valid decision.

The registered definitions stay primary, because rules were fixed against them. The added ones are sensitivity results.

## Inputs and gate

Saved scores and frozen thresholds for: `runs/event-study`, `runs/seq-study`, `runs/gaps/seed{1791,2791,3791,4791}`, `runs/gaps/event-{minus60,plus60}` and `runs/gaps/shift-{minus60,plus60}`. Each set uses its own events file. Alarms are rebuilt with `event_study.alarm_series`. Every cell must reproduce its frozen false-alarm count, catches and leads, or the mismatch is reported.

The chance rate for a new-alert catch uses the frozen circular-shift method on the notification sequence, with a fixed seed.

## Report

For each set: tests, catches under each definition, catches with chance below 0.5, median and maximum false alarms per day under each denominator, and the share of scored time with a valid decision. Per model and horizon, the warning and burden rules under each definition, for the combinations the frozen tables evaluate. Also the 11 catches on the twelve further intervals (addendum 3) under the new-alert definition.

## Interpretation fixed in advance

- **Warning:** the finding changes only if a combination meets the warning rule under the new-alert definition. Since new alerts are a subset of active signals, this cannot happen where none met it before, and that is said plainly. Any fall in catch counts is reported.
- **Burden:** any combination that changes between pass and fail under the decision-day denominator is named in the manuscript.
- **Manuscript:** it must state both definitions and whichever way the results fall.
