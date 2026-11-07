"""Tie-correct metrics from the frozen saved scores. Refits nothing and changes no score.

Registered metrics are recomputed. Anything labelled exploratory was chosen after viewing results.
Usage: python3.13 -B rescore.py RUN_DIR OUT_CSV OUT_EXPLORATORY_CSV
"""
import csv
import gzip
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import event_study as es


def tie_metrics(score, y):
    """AP with tied scores handled as one step; AUROC with average ranks for ties."""
    n, positives = len(y), int(y.sum())
    if not positives or positives == n:
        return None, None
    values, inverse, counts = np.unique(score, return_inverse=True, return_counts=True)
    gained = np.bincount(inverse, weights=y, minlength=len(values))[::-1]
    counts_desc = counts[::-1]
    tp, seen = np.cumsum(gained), np.cumsum(counts_desc)
    ap = float(np.sum(gained / positives * tp / seen))
    ascending = np.concatenate([[0], np.cumsum(counts)])
    average_rank = (ascending[:-1] + 1 + ascending[1:]) / 2
    rank_sum = float(average_rank[inverse][y == 1].sum())
    auroc = (rank_sum - positives * (positives + 1) / 2) / (positives * (n - positives))
    return ap, float(auroc)


def tie_ece(p, y, bins):
    """Equal-mass ECE that never splits a group of tied probabilities across bins."""
    edges = np.unique(np.quantile(p, np.linspace(0, 1, bins + 1)[1:-1]))
    group = np.searchsorted(edges, p, side="left")
    total = 0.0
    for g in np.unique(group):
        m = group == g
        total += m.sum() * abs(p[m].mean() - y[m].mean())
    return float(total / len(y))


def top_gap(p, y):
    cut = np.quantile(p, .9)
    m = p >= cut
    return float(abs(p[m].mean() - y[m].mean()))


def read_scores(path):
    with gzip.open(path, "rt") as s:
        next(s)
        rows = [line.rstrip().split(",") for line in s]
    a = np.array(rows, dtype=np.float64)
    return a[:, 0].astype(int), a[:, 1], a[:, 2], a[:, 3].astype(int)


def oracle_policy(index, margin, labels, onsets, h, q, cfg, seed):
    """Exploratory upper bound: the threshold is taken from the test block's own negatives."""
    negatives = margin[labels == 0]
    threshold = np.quantile(negatives, q)
    lo, hi = index[0], index[-1] + 1
    length = hi - lo
    score = np.full(length, -np.inf)
    score[index - lo] = margin
    valid = np.zeros(length, bool)
    valid[index - lo] = True
    y = np.full(length, -1, np.int8)
    y[index - lo] = labels
    block = np.ones(length, bool)
    local = [(k, o - lo) for k, o in onsets]
    return es.event_policy(score, threshold, valid, y, block, local, h, cfg, seed)


def main():
    run = Path(sys.argv[1])
    record = json.loads((run / "run.json").read_text())
    cfg = record["config"]
    first = None
    events = record["events"]
    with open(sys.argv[2], "w", newline="") as a, open(sys.argv[3], "w", newline="") as b:
        main_out = csv.writer(a)
        main_out.writerow(["fold", "kind", "h", "model", "windows", "positives", "prevalence", "ap", "ap_over_prevalence",
                           "auroc", "distinct_scores", "bss_uncal", "bss_platt", "slope_uncal", "slope_platt",
                           "platt_b", "ece5_platt", "ece10_platt", "ece15_platt", "ece10_uncal", "top_gap_platt",
                           "caught", "failures", "leads", "chance", "fa_day", "fa", "unscorable", "scored_days",
                           "oof_positive", "gate"])
        extra = csv.writer(b)
        extra.writerow(["fold", "h", "model", "q", "caught", "failures", "lead", "chance", "fa_day", "peak_percentile"])
        minute0 = None
        for r in record["results"]:
            scores = run / "scores" / f"{r['fold']}_h{r['h']}_{r['model']}.csv.gz"
            index, margin, platt, raw_y = read_scores(scores)
            m = raw_y >= 0
            y = raw_y[m].astype(float)
            ap, auroc = tie_metrics(margin[m], y)
            p, u = np.clip(platt[m], 1e-7, 1 - 1e-7), np.clip(1 / (1 + np.exp(-margin[m])), 1e-7, 1 - 1e-7)
            po = r["policy"]
            f = po["failures"]
            prevalence = float(y.mean())
            main_out.writerow([r["fold"], r["kind"], r["h"], r["model"], int(m.sum()), int(y.sum()), prevalence, ap,
                               ap / prevalence if ap is not None else None, auroc, len(np.unique(margin[m])),
                               r["uncalibrated"].get("brier_skill"), r["platt_calibrated"].get("brier_skill"),
                               r["uncalibrated"].get("calibration_slope"), r["platt_calibrated"].get("calibration_slope"),
                               r["platt"][1], tie_ece(p, y, 5), tie_ece(p, y, 10), tie_ece(p, y, 15), tie_ece(u, y, 10),
                               top_gap(p, y), sum(v.get("caught", False) for v in f.values()), len(f),
                               ";".join(str(v.get("first_lead_minutes")) for v in f.values()),
                               ";".join(str(v.get("chance_rate_under_circular_shift")) for v in f.values()),
                               po["false_alarms_per_day"], po["false_alarm_episodes"], po["unscorable_alarm_episodes"],
                               po["scored_days"], r["oof_positive"], r["gate"]])
            if r["kind"] != "A":
                continue
            # The grid origin is recovered from the block table, since indices are grid offsets.
            base = events[0]["onset"] - 0
            origin = record["input"]["first"]
            from datetime import datetime
            zero = int((datetime.fromisoformat(origin) - datetime(1970, 1, 1)).total_seconds() // 60)
            onsets = [(e["id"], e["onset"] - zero) for e in events if index[0] <= e["onset"] - zero <= index[-1]]
            negatives = np.sort(margin[m][y == 0])
            positive = margin[m][y == 1]
            peak = float(np.searchsorted(negatives, positive.max(), side="left") / len(negatives))
            for q in (.9, .95, .98, .99):
                out = oracle_policy(index, margin, raw_y, onsets, r["h"], q, cfg, cfg["seed"])
                g = out["failures"]
                extra.writerow([r["fold"], r["h"], r["model"], q, sum(v.get("caught", False) for v in g.values()), len(g),
                                ";".join(str(v.get("first_lead_minutes")) for v in g.values()),
                                ";".join(str(v.get("chance_rate_under_circular_shift")) for v in g.values()),
                                out["false_alarms_per_day"], peak])


if __name__ == "__main__":
    main()
