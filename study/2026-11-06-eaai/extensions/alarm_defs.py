"""Addendum 4: catches as active signal or new alert; false alarms per monitored or decision day. Fits nothing."""
import csv, gzip, json, statistics as st, sys
from pathlib import Path
sys.path.insert(0, "extensions")
import numpy as np, event_study as es

D = es.load_minutes("../../data/raw/MetroPT3(AirCompressor).csv")
n, first = len(D["grid"]), D["first"]
base = "provenance/event-study-config.json"; timing = "provenance/event-study-config-timing.json"
EV0 = "provenance/event-study-events.csv"
SETS = [("registered", "runs/event-study", EV0, base), ("registered", "runs/seq-study", EV0, base)]
SETS += [(f"seed{s}", f"runs/gaps/seed{s}", EV0, base) for s in (1791, 2791, 3791, 4791)]
for tag, e in (("minus60", "provenance/events-minus60.csv"), ("plus60", "provenance/events-plus60.csv")):
    SETS += [(tag, f"runs/gaps/event-{tag}", e, timing), (tag, f"runs/gaps/shift-{tag}", e, timing)]


def results(path):
    j = json.load(open(path + "/run.json")).get("results")
    if j:
        return j
    return [json.loads(l) for l in open(path + "/results.jsonl")]


rows, mism = [], []
for name, path, evf, cf in SETS:
    cfg = json.load(open(cf)); ev = es.read_events(evf, cfg)
    y, _, _ = es.build_labels(D, ev, cfg)
    ranges, emb = es.block_ranges(ev, first, n, cfg["embargo_minutes"])
    folds = {f["name"]: f for f in es.folds_for(4, ranges, ev, first)}
    L = cfg["lookback_minutes"]
    for r in results(path):
        if r.get("status") != "done" or r["fold"] not in folds or "policy" not in r:
            continue
        fold, h, model = r["fold"], int(r["h"]), r["model"]
        fn = Path(f"{path}/scores/{fold}_h{h}_{model}.csv.gz")
        if not fn.exists():
            mism.append((name, fold, h, model, "no score file")); continue
        arr = np.loadtxt(gzip.open(fn, "rt"), delimiter=",", skiprows=1, ndmin=2)
        idx = arr[:, 0].astype(int)
        f = folds[fold]
        if f.get("test_after") is not None:
            test = np.zeros(n, bool); test[f["test_after"]:] = True
        else:
            test = es.block_mask(n, ranges, f["test"], emb)
        if model in ("M5", "M6"):
            test = test & (np.arange(n) >= L)
        score = np.full(n, -np.inf); score[idx] = arr[:, 1]
        valid = np.zeros(n, bool); valid[idx] = True
        alarms, raw = es.alarm_series(score, r["policy"]["threshold"], valid, cfg)
        false4 = int(np.sum(alarms & test & (y[h] == 0)))
        if false4 != r["policy"]["false_alarm_episodes"]:
            mism.append((name, fold, h, model, "fa", false4, r["policy"]["false_alarm_episodes"]))
        i = np.flatnonzero(test); a0, a1 = int(i[0]), int(i[-1]) + 1
        rng = np.random.default_rng(cfg["seed"] + h)
        span = alarms[a0:a1]; c = np.r_[0, np.cumsum(np.r_[span, span])]; length = a1 - a0
        tests = act = act_v = new = new_v = 0
        for e in ev:
            if not test[max(e["onset"] - first - 1, 0)]:
                continue
            onset = e["onset"] - first; tests += 1
            lo, hi = max(onset - h, a0), onset - cfg["min_response_minutes"]
            fz = r["policy"]["failures"].get(e["id"], {})
            hits = np.flatnonzero(raw[lo:hi]) if hi > lo else np.array([], int)
            lead = int(onset - (lo + hits[0])) if len(hits) else None
            if bool(len(hits)) != bool(fz.get("caught")) or lead != fz.get("first_lead_minutes"):
                mism.append((name, fold, h, model, e["id"], lead, fz.get("first_lead_minutes")))
            if fz.get("caught"):
                act += 1; act_v += fz["chance_rate_under_circular_shift"] < .5
            nw = np.flatnonzero(alarms[lo:hi]) if hi > lo else np.array([], int)
            if len(nw):
                new += 1
                width = hi - lo
                st_ = (lo - a0 - rng.integers(1, length, cfg["circular_shifts"])) % length
                new_v += float(np.mean(c[st_ + width] - c[st_] > 0)) < .5
        mon = float((test & (y[h] >= 0)).sum()) / 1440
        dec = float((test & valid & (y[h] >= 0)).sum()) / 1440
        rows.append(dict(set=name, fold=fold, kind=r["kind"], h=h, model=model, tests=tests, active=act, active_valid=act_v, new=new, new_valid=new_v,
                         fa=false4, monitored_days=round(mon, 4), decision_days=round(dec, 4), fa_monitored=false4 / mon if mon else 0, fa_decision=false4 / dec if dec else 0))
print("cells", len(rows), "mismatches", len(mism), mism[:15])
with open("tables/alarm-def-cells.csv", "w", newline="") as x:
    w = csv.DictWriter(x, list(rows[0])); w.writeheader(); w.writerows(rows)
print("== by set")
for s in ("registered", "seed1791", "seed2791", "seed3791", "seed4791", "minus60", "plus60"):
    z = [r for r in rows if r["set"] == s]
    m, d = sum(r["monitored_days"] for r in z), sum(r["decision_days"] for r in z)
    print(s, "cells", len(z), "tests", sum(r["tests"] for r in z), "active", sum(r["active"] for r in z), "valid", sum(r["active_valid"] for r in z), "new", sum(r["new"] for r in z), "new valid", sum(r["new_valid"] for r in z), "decision share %.3f" % (d / m))
print("seeds together: active", sum(r["active"] for r in rows if r["set"].startswith("seed")), "new", sum(r["new"] for r in rows if r["set"].startswith("seed")), "of", sum(r["tests"] for r in rows if r["set"].startswith("seed")))
print("caught cells:", [(r["set"], r["fold"], r["h"], r["model"], r["active"], r["new"]) for r in rows if r["active"] and r["set"] in ("registered", "seed1791", "seed2791", "seed3791", "seed4791")])
print("== rules")
out = []
for s in ("registered", "seed1791", "seed2791", "seed3791", "seed4791", "minus60", "plus60"):
    z = [r for r in rows if r["set"] == s]
    for m in ("M1", "M2", "M3", "M4", "M5", "M6"):
        for h in (30, 60, 180, 360, 720):
            A = [r for r in z if r["model"] == m and r["h"] == h and r["kind"] == "A"]
            E = [r for r in z if r["model"] == m and r["h"] == h and r["kind"] == "E"]
            if len(A) != 4 or not E:
                continue
            fm, fd = st.median(r["fa_monitored"] for r in A), st.median(r["fa_decision"] for r in A)
            out.append(dict(set=s, model=m, h=h, active_valid=sum(r["active_valid"] for r in A), new_valid=sum(r["new_valid"] for r in A), warn_active=sum(r["active_valid"] for r in A) >= 3, warn_new=sum(r["new_valid"] for r in A) >= 3,
                            fa_A_monitored=round(fm, 3), fa_E_monitored=round(E[0]["fa_monitored"], 3), fa_A_decision=round(fd, 3), fa_E_decision=round(E[0]["fa_decision"], 3),
                            burden_monitored=fm <= 1 and E[0]["fa_monitored"] <= 1, burden_decision=fd <= 1 and E[0]["fa_decision"] <= 1))
with open("tables/alarm-def-rules.csv", "w", newline="") as x:
    w = csv.DictWriter(x, list(out[0])); w.writeheader(); w.writerows(out)
for s in ("registered", "seed1791", "seed2791", "seed3791", "seed4791", "minus60", "plus60"):
    z = [r for r in out if r["set"] == s]
    print(s, "combos", len(z), "warn active", sum(r["warn_active"] for r in z), "warn new", sum(r["warn_new"] for r in z), "burden monitored", sum(r["burden_monitored"] for r in z), "burden decision", sum(r["burden_decision"] for r in z))
    print("  flips:", [(r["model"], r["h"], r["fa_A_monitored"], r["fa_E_monitored"], r["fa_A_decision"], r["fa_E_decision"]) for r in z if r["burden_monitored"] != r["burden_decision"]])
    print("  max active_valid", max(r["active_valid"] for r in z), "max new_valid", max(r["new_valid"] for r in z), [(r["model"], r["h"], r["active_valid"], r["new_valid"]) for r in z if r["active_valid"] >= 2])
# Addendum 3 catches under the new-alert definition.
cfg = json.load(open(base)); ev = es.read_events(EV0, cfg); y, _, _ = es.build_labels(D, ev, cfg)
ranges, emb = es.block_ranges(ev, first, n, cfg["embargo_minutes"]); folds = {f["name"]: f for f in es.folds_for(4, ranges, ev, first)}
T = {r["nr"]: es.epoch_minute(r["start"] + ":00") - first for r in csv.DictReader(open("provenance/toribio2026-table1-intervals.csv"))}
RES = {(r["fold"], int(r["h"]), r["model"]): r for p in ("runs/event-study", "runs/seq-study") for r in json.load(open(p + "/run.json"))["results"] if r.get("status") == "done"}
count = new11 = 0; nA = 0
for r in csv.DictReader(open("tables/extra16-intervals.csv")):
    if r["caught"] != "1":
        continue
    key = (r["fold"], int(r["h"]), r["model"]); R = RES[key]; h = key[1]
    p = "runs/seq-study" if r["model"] in ("M5", "M6") else "runs/event-study"
    arr = np.loadtxt(gzip.open(f"{p}/scores/{r['fold']}_h{h}_{r['model']}.csv.gz", "rt"), delimiter=",", skiprows=1)
    idx = arr[:, 0].astype(int); score = np.full(n, -np.inf); score[idx] = arr[:, 1]; valid = np.zeros(n, bool); valid[idx] = True
    al, _ = es.alarm_series(score, R["policy"]["threshold"], valid, cfg)
    s = T[r["interval"][1:]]; has = bool(al[s - h:s - cfg["min_response_minutes"]].any())
    count += 1; new11 += has; nA += has and r["kind"] == "A"
print("further intervals: caught", count, "as new alerts", new11, "in analysis A", nA)
A = [r for r in rows if r["set"] == "registered" and r["kind"] == "A"]
print("registered analysis A decision share %.3f" % (sum(r["decision_days"] for r in A) / sum(r["monitored_days"] for r in A)))
F = [r for r in rows if r["set"] == "registered" and r["kind"] in ("C", "D")]
print("forward tests", sum(r["tests"] for r in F), "caught", sum(r["active"] for r in F), "new", sum(r["new"] for r in F), "max FA/day C,D monitored", round(max(r["fa_monitored"] for r in F), 2))
