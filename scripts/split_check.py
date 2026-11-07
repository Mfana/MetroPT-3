"""Check a chronological 60/20/20 split of MetroPT-3 against the UCI failure reports.
Standard library only. Usage: python3 -I split_check.py <csv>"""
import csv, sys, statistics as st
from array import array
from bisect import bisect_left, bisect_right
from collections import Counter
from datetime import datetime as D, timedelta as T

path = sys.argv[1]
F = [(1, D(2020, 4, 18, 0, 0), D(2020, 4, 18, 23, 59)),
     (2, D(2020, 5, 29, 23, 30), D(2020, 5, 30, 6, 0)),
     (3, D(2020, 6, 5, 10, 0), D(2020, 6, 7, 14, 30)),
     (4, D(2020, 7, 15, 14, 30), D(2020, 7, 15, 19, 0))]
HORIZONS = [0.5, 1, 3, 6, 12]
REPORTED = {0.5: (.931, .918, .028), 1: (.918, .893, .034), 3: (.889, .851, .056),
            6: (.842, .796, .089), 12: (.771, .724, .137)}
VARS = ["TP2", "TP3", "Reservoirs", "Oil_temperature", "Motor_current"]

ts = array("d")
cols = {v: array("f") for v in VARS}
comp = array("b")
bad = 0
with open(path, newline="") as fh:
    r = csv.reader(fh)
    h = next(r)
    print("header:", h)
    it, ic = h.index("timestamp"), h.index("COMP")
    idx = {v: h.index(v) for v in VARS}
    for row in r:
        try:
            t = D.strptime(row[it], "%Y-%m-%d %H:%M:%S").timestamp()
            vals = {v: float(row[i]) for v, i in idx.items()}
            c = int(float(row[ic]))
        except (ValueError, IndexError):
            bad += 1
            continue
        ts.append(t)
        for v in VARS:
            cols[v].append(vals[v])
        comp.append(c)

n = len(ts)
fmt = lambda x: D.fromtimestamp(x).strftime("%Y-%m-%d %H:%M:%S")
print(f"\nrows={n} unparsable={bad} first={fmt(ts[0])} last={fmt(ts[-1])}")
diffs = [ts[i + 1] - ts[i] for i in range(n - 1)]
print("monotonic:", all(d > 0 for d in diffs), "non-increasing steps:", sum(d <= 0 for d in diffs))
print("top step sizes (s):", Counter(round(d) for d in diffs).most_common(6))
gaps = sorted(((d, i) for i, d in enumerate(diffs) if d > 3600), reverse=True)
print(f"gaps >1h: {len(gaps)}; total {sum(g[0] for g in gaps) / 3600:.1f} h")
for d, i in gaps[:8]:
    print(f"  {d / 3600:7.1f} h  from {fmt(ts[i])} to {fmt(ts[i + 1])}")

print("\nrows per month:")
for m, c in sorted(Counter(D.fromtimestamp(x).strftime("%Y-%m") for x in ts).items()):
    print(" ", m, c)

b60, b80 = int(n * .6), int(n * .8)
parts = [("dev", 0, b60), ("val", b60, b80), ("test", b80, n)]
print("\n60/20/20 by row:")
for name, a, b in parts:
    print(f"  {name:5s} rows {a}-{b - 1} n={b - a}  {fmt(ts[a])} -> {fmt(ts[b - 1])}")

print("\nfailures by position:")
for k, a, b in F:
    i, j = bisect_left(ts, a.timestamp()), bisect_right(ts, b.timestamp())
    where = [p for p, x, y in parts if i < y and j > x]
    print(f"  #{k} {a} -> {b}: rows {i}-{j - 1} n={j - i}, frac {i / n:.4f}-{j / n:.4f}, partition(s) {where}")

print(f"\nrows after end of last failure: {n - bisect_right(ts, F[-1][2].timestamp())} "
      f"({(n - bisect_right(ts, F[-1][2].timestamp())) / n:.2%}); test starts at frac 0.8000")

fail_ranges = [(bisect_left(ts, a.timestamp()), bisect_right(ts, b.timestamp())) for _, a, b in F]
in_fail = bytearray(n)
for i, j in fail_ranges:
    in_fail[i:j] = b"\x01" * (j - i)

print("\npositive rows per horizon, window = [start-h, start), excluding failure rows")
print("h     total  prev_all   dev    val   test | prev_val  per-event rows")
for hz in HORIZONS:
    pos = bytearray(n)
    per = []
    for _, a, _b in F:
        i = bisect_left(ts, (a - T(hours=hz)).timestamp())
        j = bisect_left(ts, a.timestamp())
        c = 0
        for k in range(i, j):
            if not in_fail[k]:
                pos[k] = 1
                c += 1
        per.append(c)
    tot = sum(pos)
    dv, vl, te = sum(pos[0:b60]), sum(pos[b60:b80]), sum(pos[b80:n])
    p, rec, far = REPORTED[hz]
    odds = far * p / (rec * (1 - p))
    print(f"{hz:<5} {tot:6d} {tot / n:7.3%} {dv:6d} {vl:6d} {te:6d} | {vl / (b80 - b60):7.3%}  {per}  "
          f"paper-implied prev {odds / (1 + odds):.1%}; precision at real prev "
          f"{rec * (tot / n) / (rec * (tot / n) + far * (1 - tot / n)):.1%}")
print("failure rows total:", sum(in_fail), f"({sum(in_fail) / n:.2%}); in test: {sum(in_fail[b80:n])}")


def summ(sel, label):
    print(f"  {label} (n={len(sel)})")
    for v in VARS:
        x = [cols[v][i] for i in sel]
        if x:
            print(f"    {v:16s} mean {st.fmean(x):7.3f} sd {st.pstdev(x):6.3f}")


pre = bytearray(n)
for _, a, _b in F:
    for k in range(bisect_left(ts, (a - T(hours=6)).timestamp()), bisect_left(ts, a.timestamp())):
        if not in_fail[k]:
            pre[k] = 1
nor = [i for i in range(n) if not in_fail[i] and not pre[i]]
prei = [i for i in range(n) if pre[i]]
fai = [i for i in range(n) if in_fail[i]]
print("\nstate means, all rows (pre-failure = 6 h before start):")
summ(nor, "normal"); summ(prei, "pre-failure"); summ(fai, "failure")
print("state means, COMP==1 (intake valve signal active: compressor off or offloaded):")
for lab, s in [("normal", nor), ("pre-failure", prei), ("failure", fai)]:
    summ([i for i in s if comp[i] == 1], lab)
print("state means, COMP==0 (compressor taking in air, under load):")
for lab, s in [("normal", nor), ("pre-failure", prei), ("failure", fai)]:
    summ([i for i in s if comp[i] == 0], lab)

x = sorted(cols["TP2"])
print("\nTP2 quantiles:", {q: round(x[int(q * (n - 1))], 3) for q in (0, .1, .25, .5, .75, .9, .99, 1)})
print(f"TP2 < 1 bar: {sum(v < 1 for v in x) / n:.1%}; TP2 >= 7 bar: {sum(v >= 7 for v in x) / n:.1%}")
print("COMP share:", {k: f"{v / n:.1%}" for k, v in Counter(comp).items()})
