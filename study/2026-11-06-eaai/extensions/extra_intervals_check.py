"""Read-only look: how do the 12 extra intervals in Toribio et al. (2026, Table 1) relate to loaded runs? Fits nothing."""
import json, sys
from datetime import datetime as D
sys.path.insert(0, "extensions")
import numpy as np, event_study as es

X = [("4/12 11:50", "4/12 23:30"), ("4/29 03:20", "4/29 04:00"), ("4/29 22:00", "4/29 22:20"), ("5/13 14:00", "5/13 23:59"),
     ("5/18 05:00", "5/18 05:30"), ("5/19 10:10", "5/19 11:00"), ("5/19 22:10", "5/20 20:00"), ("5/23 09:50", "5/23 10:10"),
     ("6/01 15:00", "6/01 15:40"), ("6/03 10:00", "6/03 11:00"), ("7/08 17:30", "7/08 19:00"), ("7/17 04:30", "7/17 05:30")]
base = json.load(open("provenance/event-study-config.json"))
ev = es.read_events("provenance/event-study-events.csv", base)
d = es.load_minutes("../../data/raw/MetroPT3(AirCompressor).csv")
g, names, first, pres = d["grid"], d["names"], d["first"], d["present"]
print("first type", type(first), first, "onset type", type(ev[0]["onset"]), ev[0]["onset"])
# Convert wall-clock to grid index using a known anchor: 29 May report onset 23:30.
anchor = ev[1]["onset"] - first
A = D(2020, 5, 29, 23, 30)
idx = lambda s: anchor + int((D.strptime("2020/" + s, "%Y/%m/%d %H:%M") - A).total_seconds() // 60)
iv = [(idx(a), idx(b), a, b) for a, b in X]
comp = g[:, names.index("COMP")]
loaded = (comp < .5) & pres
dd = np.diff(np.r_[0, loaded.astype(int), 0]); st = np.flatnonzero(dd == 1); en = np.flatnonzero(dd == -1); runs = np.c_[st, en - st]
on = [e["onset"] - first for e in ev]; end = [e["end"] - first for e in ev]
near = lambda s: any(o - 120 <= s <= b for o, b in zip(on, end))
tot = int(pres.sum())
ins = sum(int(pres[a:b].sum()) for a, b, *_ in iv)
print("extra interval minutes present", ins, "of", tot, "share %.3f%%" % (100 * ins / tot))
for a, b, sa, sb in iv:
    seg = np.arange(a, b)
    r = [(int(s - a), int(l)) for s, l in runs if a - 120 <= s <= b and l >= 30]
    print(sa, "-", sb, "len", b - a, "present", int(pres[seg].sum()), "loaded share %.2f" % (loaded[seg].mean()), "runs>=30 (start rel, len):", r,
          "days to next report %.1f" % min([(o - a) / 1440 for o in on if o >= a], default=float("nan")))
for L in (30, 60, 120, 240):
    away = [(s, l) for s, l in runs if l >= L and not near(s)]
    hit = [(s, l) for s, l in away if any(a - 120 <= s <= b for a, b, *_ in iv)]
    ov = [(s, l) for s, l in away if any(s < b and s + l > a for a, b, *_ in iv)]
    print("runs >=", L, ": away", len(away), "start within -120..end of an extra interval", len(hit), "overlap one", len(ov))
away = [(s, l) for s, l in runs if l >= 240 and not near(s)]
print("away runs >=240:", [((np.datetime64("2020-05-29T23:30") + np.timedelta64(int(s - anchor), "m")).astype(str), int(l)) for s, l in away])
# Rate of loaded-run starts inside the same windows if the 12 windows were placed at random, keeping their lengths (rotations).
rng = np.random.default_rng(1791)
for L in (30, 240):
    away = np.array([s for s, l in runs if l >= L and not near(s)])
    obs = sum(any(a - 120 <= s <= b for a, b, *_ in iv) for s in away)
    n = len(pres); c = []
    for off in rng.integers(0, n, 1000):
        c.append(sum(any(((a + off) % n) - 120 <= s <= ((b + off) % n) for a, b, *_ in iv) for s in away))
    print("L", L, "observed", obs, "of", len(away), "rotated median", float(np.median(c)), "p95", float(np.percentile(c, 95)), "share rotated >= obs", float(np.mean(np.array(c) >= obs)))
