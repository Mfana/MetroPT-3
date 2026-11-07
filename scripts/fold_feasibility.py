"""Per-event feasibility numbers for the event-held-out protocol.
Standard library only. Usage: python3 -I scripts/fold_feasibility.py <csv>"""
import csv, sys
from array import array
from bisect import bisect_left, bisect_right
from datetime import datetime as D, timedelta as T

F = [(1, D(2020, 4, 18, 0, 0), D(2020, 4, 18, 23, 59)),
     (2, D(2020, 5, 29, 23, 30), D(2020, 5, 30, 6, 0)),
     (3, D(2020, 6, 5, 10, 0), D(2020, 6, 7, 14, 30)),
     (4, D(2020, 7, 15, 14, 30), D(2020, 7, 15, 19, 0))]
HORIZONS = [0.5, 1, 3, 6, 12]
MAINT = {3: D(2020, 6, 8, 16, 0), 4: D(2020, 7, 16, 0, 0)}

ts, comp = array("d"), array("b")
with open(sys.argv[1], newline="") as fh:
    r = csv.reader(fh)
    h = next(r)
    it, ic = h.index("timestamp"), h.index("COMP")
    for row in r:
        ts.append(D.strptime(row[it], "%Y-%m-%d %H:%M:%S").timestamp())
        comp.append(int(float(row[ic])))
n = len(ts)
fmt = lambda x: D.fromtimestamp(x).strftime("%Y-%m-%d %H:%M:%S")
idx = lambda d: bisect_left(ts, d.timestamp())

print("Pre-failure window coverage and load state, per event")
print("event horizon rows expected coverage under_load off_or_offloaded load_share longest_gap_min")
for k, a, b in F:
    for hz in HORIZONS:
        i, j = idx(a - T(hours=hz)), idx(a)
        cnt = j - i
        exp = hz * 360
        load = sum(1 for x in range(i, j) if comp[x] == 0)
        lg = max((ts[x + 1] - ts[x] for x in range(i, j - 1)), default=0) / 60
        print(f"#{k} {hz:>4} {cnt:6d} {exp:7.0f} {cnt / exp:6.1%} {load:6d} {cnt - load:6d} "
              f"{(load / cnt if cnt else 0):6.1%} {lg:8.1f}")

print("\nDuring-failure rows")
for k, a, b in F:
    i, j = idx(a), bisect_right(ts, b.timestamp())
    load = sum(1 for x in range(i, j) if comp[x] == 0)
    print(f"#{k} rows {j - i} under_load {load} ({load / (j - i):.1%})")

print("\nFailure end to maintenance (rows are excluded as neither normal nor positive)")
for k, a, b in F:
    if k in MAINT:
        i, j = bisect_right(ts, b.timestamp()), idx(MAINT[k])
        print(f"#{k} {b} -> {MAINT[k]}: {(MAINT[k] - b).total_seconds() / 3600:.1f} h, {j - i} rows")

print("\nSpacing between failures")
for (k1, _, e1), (k2, s2, _) in zip(F, F[1:]):
    print(f"#{k1} end -> #{k2} start: {(s2 - e1).total_seconds() / 86400:.2f} days")

print("\nRows and load share in each candidate block (midpoints between failures as boundaries)")
bounds = [ts[0]]
for (_, _, e1), (_, s2, _) in zip(F, F[1:]):
    bounds.append(e1.timestamp() + (s2.timestamp() - e1.timestamp()) / 2)
bounds.append(ts[-1] + 1)
for q in range(4):
    i, j = bisect_left(ts, bounds[q]), bisect_left(ts, bounds[q + 1])
    load = sum(1 for x in range(i, j) if comp[x] == 0)
    print(f"block {q + 1} (contains #{q + 1}): {fmt(ts[i])} -> {fmt(ts[j - 1])}, rows {j - i} "
          f"({(j - i) / n:.1%}), load share {load / (j - i):.1%}")

print("\nHoldout after #4 with no reported failure")
i = bisect_right(ts, F[3][2].timestamp())
print(f"rows after #4: {n - i} ({(n - i) / n:.1%}); from {fmt(ts[i])}; "
      f"from 16 Jul maintenance: {n - idx(MAINT[4])}; load share "
      f"{sum(1 for x in range(idx(MAINT[4]), n) if comp[x] == 0) / (n - idx(MAINT[4])):.1%}")
