"""Addendum 3: saved-score test against the twelve further intervals. Fits nothing. Run from the study folder."""
import csv, gzip, json, sys
from pathlib import Path
sys.path.insert(0, "extensions")
import numpy as np, event_study as es

SHIFTS, SEED = 1000, 791
cfg = json.load(open("provenance/event-study-config.json"))
ev4 = es.read_events("provenance/event-study-events.csv", cfg)
d = es.load_minutes("../../data/raw/MetroPT3(AirCompressor).csv")
n, first, present = len(d["grid"]), d["first"], d["present"]
extra = []
for r in csv.DictReader(open("provenance/toribio2026-table1-intervals.csv")):
    if r["in_company_reports"] == "no":
        a, b = es.epoch_minute(r["start"] + ":00"), es.epoch_minute(r["end"] + ":00")
        extra.append({"id": "x" + r["nr"], "onset": a, "end": b, "release": b + cfg["default_recovery_minutes"]})
assert len(extra) == 12
ev16 = sorted(ev4 + extra, key=lambda e: e["onset"])
ev16_norec = sorted(ev4 + [dict(e, release=e["end"] + 1) for e in extra], key=lambda e: e["onset"])
y4, _, _ = es.build_labels(d, ev4, cfg)
y16, _, _ = es.build_labels(d, ev16, cfg)
y16n, _, _ = es.build_labels(d, ev16_norec, cfg)
ranges, embargo = es.block_ranges(ev4, first, n, cfg["embargo_minutes"])
folds = {f["name"]: f for f in es.folds_for(4, ranges, ev4, first)}
L = cfg["lookback_minutes"]
comp = d["grid"][:, d["names"].index("COMP")]
loaded = (comp < .5) & present
dd = np.diff(np.r_[0, loaded.astype(int), 0]); st_, en_ = np.flatnonzero(dd == 1), np.flatnonzero(dd == -1)
runs = [(int(s), int(e - s)) for s, e in zip(st_, en_) if e - s >= 30]
# Time that makes a warning window unscorable: any other interval's active period, or a report's active or recovery period.
busy4 = np.zeros(n, bool)
for e in ev4:
    busy4[max(e["onset"] - first, 0):min(e["release"] - first, n)] = True
active = {e["id"]: (e["onset"] - first, e["end"] - first) for e in extra}


def test_mask(f):
    if f.get("test_after") is not None:
        t = np.zeros(n, bool); t[f["test_after"]:] = True
    else:
        t = es.block_mask(n, ranges, f["test"], embargo)
    return t


def auroc_shift(score, pos, rng):
    """Tied-rank AUROC over valid minutes, with the positive mask rotated by random offsets."""
    if pos.sum() == 0 or pos.sum() == len(pos):
        return None, None
    u, inv, cnt = np.unique(score, return_inverse=True, return_counts=True)
    cum = np.cumsum(cnt); rank = (cum - (cnt - 1) / 2)[inv]
    p, m = int(pos.sum()), len(pos)
    auc = (rank[pos].sum() - p * (p + 1) / 2) / (p * (m - p))
    c = np.r_[0, np.cumsum(np.r_[rank, rank])]
    idx = np.flatnonzero(pos)
    # Rotate the positive pattern by summing rank over shifted indices.
    offs = rng.integers(1, m, SHIFTS)
    sh = np.array([rank[(idx + o) % m].sum() for o in offs])
    auc_s = (sh - p * (p + 1) / 2) / (p * (m - p))
    return float(auc), float(np.mean(auc_s >= auc))


cells = []
mismatch = []
for path, rows in (("runs/event-study", None), ("runs/seq-study", None)):
    for r in json.load(open(path + "/run.json"))["results"]:
        if r["status"] == "done" and r["fold"] in folds:  # The exploratory random split is not a registered fold.
            cells.append((path, r))
print("cells", len(cells))
OUT, EV, RANK = [], [], []
for path, r in cells:
    fold, h, model = r["fold"], int(r["h"]), r["model"]
    arr = np.loadtxt(gzip.open(f"{path}/scores/{fold}_h{h}_{model}.csv.gz", "rt"), delimiter=",", skiprows=1)
    idx = arr[:, 0].astype(int); margin = arr[:, 1]
    assert np.all(y4[h][idx] == arr[:, 3].astype(int)), (fold, h, model)
    test = test_mask(folds[fold])
    if model in ("M5", "M6"):
        test = test & (np.arange(n) >= L)
    score = np.full(n, -np.inf); score[idx] = margin
    valid = np.zeros(n, bool); valid[idx] = True
    th = r["policy"]["threshold"]
    alarms, raw = es.alarm_series(score, th, valid, cfg)
    # Gate: reproduce the frozen policy.
    false4 = int(np.sum(alarms & test & (y4[h] == 0)))
    onsets = [(e["id"], e["onset"] - first) for e in ev4 if test[max(e["onset"] - first - 1, 0)]]
    i0, i1 = np.flatnonzero(test)[[0, -1]]; a0, a1 = int(i0), int(i1) + 1
    rep_caught, rep_valid, rep_tests = 0, 0, 0
    for key, onset in onsets:
        lo, hi = max(onset - h, a0), onset - cfg["min_response_minutes"]
        hits = np.flatnonzero(raw[lo:hi]) if hi > lo else np.array([], int)
        fz = r["policy"]["failures"][key]
        lead = int(onset - (lo + hits[0])) if len(hits) else None
        if bool(len(hits)) != bool(fz["caught"]) or lead != fz.get("first_lead_minutes"):
            mismatch.append((fold, h, model, key, "catch", bool(len(hits)), fz["caught"], lead, fz.get("first_lead_minutes")))
        rep_tests += 1
        if fz["caught"]:
            rep_caught += 1
            rep_valid += fz["chance_rate_under_circular_shift"] < .5
    if false4 != r["policy"]["false_alarm_episodes"]:
        mismatch.append((fold, h, model, "fa", false4, r["policy"]["false_alarm_episodes"]))
    days4 = float((test & (y4[h] >= 0)).sum()) / 1440
    false16 = int(np.sum(alarms & test & (y16[h] == 0))); days16 = float((test & (y16[h] >= 0)).sum()) / 1440
    false16n = int(np.sum(alarms & test & (y16n[h] == 0))); days16n = float((test & (y16n[h] >= 0)).sum()) / 1440
    rng = np.random.default_rng(SEED + h)
    span = raw[a0:a1]; length = a1 - a0
    c = np.r_[0, np.cumsum(np.r_[span, span])]
    x_tests = x_caught = x_valid = x_before = x_active = x_inblock = 0
    for e in extra:
        s, t_ = active[e["id"]]
        if not (a0 <= s < a1) or not test[max(s - 1, 0)]:
            continue
        x_inblock += 1
        lo, hi = s - h, s - cfg["min_response_minutes"]
        other = np.zeros(n, bool)
        for k, (u, v) in active.items():
            if k != e["id"]:
                other[max(u, 0):v + 1] = True
        scorable = lo >= a0 and hi > lo and test[lo:hi].all() and not other[lo:hi].any() and not busy4[lo:hi].any()
        activeh = bool(raw[s:t_ + 1].any())
        x_active += activeh
        rec = dict(fold=fold, kind=r["kind"], h=h, model=model, interval=e["id"], scorable=int(scorable), active_alarm=int(activeh), caught="", lead="", chance="", before_run="")
        if scorable:
            x_tests += 1
            hits = np.flatnonzero(raw[lo:hi])
            width = hi - lo
            starts = (lo - a0 - rng.integers(1, length, cfg["circular_shifts"])) % length
            chance = float(np.mean(c[starts + width] - c[starts] > 0))
            rec.update(caught=int(len(hits) > 0), chance=chance)
            if len(hits):
                at = lo + int(hits[0]); lead = s - at
                x_caught += 1; x_valid += chance < .5
                # The sustained loaded run that begins within 120 min before the start, if any.
                prior = [q for q, l_ in runs if s - 120 <= q <= s]
                before = (not prior) or at < prior[0]
                rec.update(lead=lead, before_run=int(before))
                x_before += bool(chance < .5 and before)
        EV.append(rec)
    OUT.append(dict(fold=fold, kind=r["kind"], h=h, model=model, fa4=false4, days4=days4, fa_day4=false4 / days4 if days4 else 0,
                    fa16=false16, days16=days16, fa_day16=false16 / days16 if days16 else 0,
                    fa16_norec=false16n, days16_norec=days16n, fa_day16_norec=false16n / days16n if days16n else 0,
                    rep_tests=rep_tests, rep_caught=rep_caught, rep_valid=rep_valid, x_inblock=x_inblock, x_tests=x_tests, x_caught=x_caught, x_valid=x_valid, x_valid_before_run=x_before, x_active=x_active))
    if r["kind"] == "A":
        m_ = np.isin(np.arange(n), idx)
        pre = np.zeros(n, bool); act = np.zeros(n, bool)
        for e in extra:
            s, t_ = active[e["id"]]
            pre[max(s - h, 0):s] = True; act[s:t_ + 1] = True
        neg = y16[h] == 0
        for name, posm in (("warning", pre & ~act & ~busy4), ("active", act & ~busy4)):
            keep = valid & test & (neg | posm)
            sel = np.flatnonzero(keep)
            auc, share = auroc_shift(score[sel], posm[sel], rng)
            RANK.append(dict(fold=fold, h=h, model=model, target=name, positives=int(posm[sel].sum()), auroc=auc, share_at_least_observed=share))

print("gate mismatches", len(mismatch), mismatch[:20])
for name, rows in (("cells", OUT), ("intervals", EV), ("rank", RANK)):
    with open(f"tables/extra16-{name}.csv", "w", newline="") as x:
        w = csv.DictWriter(x, list(rows[0])); w.writeheader(); w.writerows(rows)
print("written", len(OUT), len(EV), len(RANK))
