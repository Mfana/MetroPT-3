"""Whole-failure, multi-horizon evaluation of MetroPT-3 with NumPy and SciPy only.

Registered by provenance/registered-plan.md. Usage:
  python3.13 -B event_study.py --csv PATH --config CONFIG --out NEW_DIR [--synthetic]
"""
import argparse
import csv
import gzip
import hashlib
import json
import multiprocessing as mp
import platform
import sys
from datetime import datetime
from itertools import combinations
from pathlib import Path

import numpy as np
from scipy.optimize import minimize
from scipy.special import expit
from scipy.stats import spearmanr

ANALOG = ["TP2", "TP3", "H1", "DV_pressure", "Reservoirs", "Motor_current", "Oil_temperature"]
DIGITAL = ["COMP", "DV_eletric", "Towers", "MPG", "LPS", "Pressure_switch", "Oil_level", "Caudal_impulses"]
FAMILIES = {"TP2": ["TP2"], "TP3+Reservoirs": ["TP3", "Reservoirs"], "H1": ["H1"], "DV_pressure": ["DV_pressure"],
            "Motor_current": ["Motor_current"], "Oil_temperature": ["Oil_temperature"],
            "Operating_state": ["COMP", "MPG", "DV_eletric", "transitions", "load6h"], "Towers": ["Towers"],
            "LPS": ["LPS"], "Pressure_switch": ["Pressure_switch"], "Oil_level": ["Oil_level"],
            "Caudal_impulses": ["Caudal_impulses"]}


def epoch_minute(text):
    return int(datetime.fromisoformat(text).timestamp() // 60) if False else int(
        (datetime.fromisoformat(text) - datetime(1970, 1, 1)).total_seconds() // 60)


def load_minutes(path):
    """Average raw rows into one-minute cells, in memory, on a regular grid."""
    sha = hashlib.sha256()
    with open(path, "rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            sha.update(chunk)
    names = ANALOG + DIGITAL
    with open(path, newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        stamps, rows, last = [], [], None
        for row in reader:
            text = row["timestamp"]
            value = (datetime.fromisoformat(text) - datetime(1970, 1, 1)).total_seconds()
            if last is not None and value <= last:
                raise ValueError("Timestamps must strictly increase")
            last = value
            stamps.append(value)
            rows.append([float(row[n]) for n in names])
    stamps = np.array(stamps)
    values = np.array(rows, dtype=np.float64)
    if not np.isfinite(values).all():
        raise ValueError("Non-finite sensor value")
    minute = (stamps // 60).astype(np.int64)
    first, n = minute[0], minute[-1] - minute[0] + 1
    index = minute - first
    count = np.bincount(index, minlength=n).astype(float)
    grid = np.full((n, len(names)), np.nan)
    with np.errstate(invalid="ignore", divide="ignore"):
        for j in range(len(names)):
            grid[:, j] = np.bincount(index, weights=values[:, j], minlength=n) / count
    return {"first": int(first), "grid": grid, "present": count > 0, "names": names,
            "raw_rows": len(stamps), "sha256": sha.hexdigest(),
            "first_timestamp": datetime.utcfromtimestamp(stamps[0]).isoformat(),
            "last_timestamp": datetime.utcfromtimestamp(stamps[-1]).isoformat()}


def rolling_sum(x, width):
    """Sum of x over the half-open window [t-width, t), for every t."""
    c = np.concatenate([[0.0], np.cumsum(x)])
    out = np.zeros(len(x) + 1)
    out[width:] = c[width:] - c[:-width]
    return out[:-1] if False else out[:len(x)]


def features(data, cfg):
    """Strictly causal: a feature at minute t reads only minutes t-L to t-1."""
    grid, present = data["grid"], data["present"].astype(float)
    names = data["names"]
    L = cfg["lookback_minutes"]
    n = len(grid)
    filled = np.nan_to_num(grid)
    cov = rolling_sum(present, L) / L
    ok = cov >= cfg["min_lookback_coverage"]
    with np.errstate(invalid="ignore", divide="ignore"):
        denom = rolling_sum(present, L)
        out, labels = [], []
        loaded = (np.nan_to_num(grid[:, names.index("COMP")], nan=1.0) < .5) & data["present"]
        offloaded = (~loaded) & data["present"]
        state_out, state_labels = [], []
        for name in ANALOG:
            x = filled[:, names.index(name)]
            mu = rolling_sum(x, L) / denom
            var = np.maximum(rolling_sum(x * x, L) / denom - mu * mu, 0)
            k = cfg["delta_edge_minutes"]
            early = rolling_sum(x, k) / rolling_sum(present, k)
            late_shift = np.full(n, np.nan)
            late_shift[L - k:] = early[:n - (L - k)]
            delta = early - late_shift
            out += [mu, np.sqrt(var), delta]
            labels += [f"{name}|mean", f"{name}|std", f"{name}|delta"]
            for tag, mask in (("load", loaded), ("off", offloaded)):
                m = rolling_sum(mask.astype(float), L)
                state_out.append(rolling_sum(x * mask, L) / m)
                state_labels.append(f"{name}|{tag}_mean")
        for name in DIGITAL:
            x = filled[:, names.index(name)]
            out.append(rolling_sum(x, L) / denom)
            labels.append(f"{name}|mean")
        comp = filled[:, names.index("COMP")]
        change = np.zeros(n)
        change[1:] = np.abs(np.diff((comp < .5).astype(float))) * present[1:] * present[:-1]
        transitions = rolling_sum(change, L)
        wide = cfg["state_history_minutes"]
        load6 = rolling_sum(loaded.astype(float), wide) / rolling_sum(present, wide)
    out += [transitions, load6]
    labels += ["transitions|count", "load6h|frac"]
    X = np.column_stack(out)
    state_block = [X[:, labels.index(k)] for k in ("COMP|mean", "transitions|count", "load6h|frac")]
    S = np.column_stack(state_out + state_block)
    S_labels = state_labels + ["COMP|mean", "transitions|count", "load6h|frac"]
    keep_state = ["COMP|mean", "MPG|mean", "DV_eletric|mean", "transitions|count", "load6h|frac"]
    Z = X[:, [labels.index(k) for k in keep_state]]
    ok = ok & np.isfinite(X).all(axis=1)
    return {"M1": (Z, keep_state), "M3": (X, labels), "M2": (X, labels), "M4": (S, S_labels)}, ok


def build_labels(data, events, cfg):
    """Return per-horizon labels (with -1 excluded), scorable mask and event ids."""
    n, first = len(data["grid"]), data["first"]
    present = data["present"].astype(float)
    excluded = np.zeros(n, bool)
    state = np.array(["normal"] * n, dtype=object)
    for e in events:
        a, b = e["onset"] - first, e["end"] - first
        release = e["release"] - first
        excluded[max(a, 0):min(b + 1, n)] = True
        state[max(a, 0):min(b + 1, n)] = "failure"
        excluded[max(b + 1, 0):min(release, n)] = True
        state[max(b + 1, 0):min(release, n)] = "recovery"
    y, episodes = {}, {}
    c = np.concatenate([[0.0], np.cumsum(present)])
    for h in cfg["horizon_minutes"]:
        label = np.zeros(n, np.int8)
        ep = np.full(n, -1, np.int16)
        for k, e in enumerate(events):
            a = e["onset"] - first
            lo = max(a - h, 0)
            label[lo:a] = 1
            ep[lo:a] = k
        follow = np.array(c[np.minimum(np.arange(n) + h, n)] - c[np.arange(n)]) / h
        censored = (follow < cfg["min_followup_coverage"]) & (label == 0)
        drop = excluded | censored | ~data["present"]
        out = label.astype(np.int8).copy()
        out[drop] = -1
        # A rolling lookback overlapping an exclusion is never positive by construction here.
        y[h], episodes[h] = out, ep
    return y, episodes, state


def block_ranges(events, first, n, embargo):
    """Midpoint blocks; each index range keeps one reported failure."""
    cuts = [0]
    for a, b in zip(events, events[1:]):
        cuts.append(int((a["end"] + b["onset"]) / 2) - first)
    cuts.append(n)
    return [(cuts[i], cuts[i + 1]) for i in range(len(cuts) - 1)], embargo


def block_mask(n, ranges, chosen, embargo=0):
    mask = np.zeros(n, bool)
    for i in chosen:
        a, b = ranges[i]
        mask[a + (embargo if a > 0 else 0):b - (embargo if b < n else 0)] = True
    return mask


# ---- Models -----------------------------------------------------------------------------------

class Logit:
    def __init__(self, l2):
        self.l2 = l2

    def fit(self, X, y, w):
        self.m = np.nanmean(X, axis=0)
        self.s = np.nanstd(X, axis=0)
        self.s[self.s < 1e-9] = 1
        Z = (np.nan_to_num(X, nan=0) - self.m) / self.s
        if np.isnan(X).any():
            Z = np.where(np.isnan(X), 0.0, (X - self.m) / self.s)
        total = w.sum()
        prior = np.average(y, weights=w)
        start = np.zeros(Z.shape[1] + 1)
        start[0] = np.log(max(prior, 1e-9) / max(1 - prior, 1e-9))

        def objective(theta):
            margin = theta[0] + Z @ theta[1:]
            loss = np.sum(w * (np.logaddexp(0, margin) - y * margin)) / total
            p = expit(margin)
            g = np.concatenate([[np.sum(w * (p - y))], Z.T @ (w * (p - y))]) / total
            pen = self.l2 * theta[1:]
            return loss + .5 * self.l2 * theta[1:] @ theta[1:], g + np.concatenate([[0], pen])
        result = minimize(objective, start, jac=True, method="L-BFGS-B", options={"maxiter": 400})
        self.theta = result.x
        return self

    def margin(self, X):
        Z = np.where(np.isnan(X), 0.0, (X - self.m) / self.s)
        return self.theta[0] + Z @ self.theta[1:]


class GBDT:
    """Logistic gradient boosting on quantile histograms. NaN goes to a dedicated bin."""

    def __init__(self, cfg, seed):
        self.trees, self.lr, self.depth = cfg["gbdt_trees"], cfg["gbdt_learning_rate"], cfg["gbdt_depth"]
        self.min_hess, self.bins, self.l2 = cfg["gbdt_min_hessian"], cfg["gbdt_bins"], cfg["gbdt_l2"]
        self.sub, self.rng = cfg["gbdt_subsample"], np.random.default_rng(seed)

    def encode(self, X):
        out = np.empty(X.shape, np.int16)
        for j, edges in enumerate(self.edges):
            out[:, j] = np.searchsorted(edges, X[:, j], side="left")
            out[np.isnan(X[:, j]), j] = self.bins
        return out

    def fit(self, X, y, w):
        qs = np.linspace(0, 1, self.bins + 1)[1:-1]
        self.edges = []
        for j in range(X.shape[1]):
            finite = X[:, j][np.isfinite(X[:, j])]
            self.edges.append(np.unique(np.quantile(finite, qs)) if len(finite) else np.array([0.0]))
        B = self.encode(X)
        prior = np.clip(np.average(y, weights=w), 1e-7, 1 - 1e-7)
        self.base = float(np.log(prior / (1 - prior)))
        F = np.full(len(y), self.base)
        self.forest = []
        for _ in range(self.trees):
            p = expit(F)
            grad, hess = w * (p - y), np.maximum(w * p * (1 - p), 1e-12)
            use = self.rng.random(len(y)) < self.sub
            tree = self._tree(B, grad, hess, np.flatnonzero(use), 0)
            self.forest.append(tree)
            F += self.lr * self._apply(tree, B)
        return self

    def _tree(self, B, g, h, idx, depth):
        G, H = g[idx].sum(), h[idx].sum()
        value = -G / (H + self.l2)
        if depth >= self.depth or H < 2 * self.min_hess or len(idx) < 4:
            return value
        best, split = 0.0, None
        parent = G * G / (H + self.l2)
        size = self.bins + 1
        for j in range(B.shape[1]):
            b = B[idx, j]
            gs = np.bincount(b, weights=g[idx], minlength=size)
            hs = np.bincount(b, weights=h[idx], minlength=size)
            gl, hl = np.cumsum(gs[:-1]), np.cumsum(hs[:-1])
            gr, hr = G - gl, H - hl
            valid = (hl >= self.min_hess) & (hr >= self.min_hess)
            if not valid.any():
                continue
            gain = np.where(valid, gl * gl / (hl + self.l2) + gr * gr / (hr + self.l2) - parent, -1)
            k = int(gain.argmax())
            if gain[k] > best:
                best, split = gain[k], (j, k)
        if split is None:
            return value
        j, k = split
        left = B[idx, j] <= k
        return (j, k, self._tree(B, g, h, idx[left], depth + 1), self._tree(B, g, h, idx[~left], depth + 1))

    def _apply(self, tree, B):
        out = np.zeros(len(B))
        stack = [(tree, np.arange(len(B)))]
        while stack:
            node, idx = stack.pop()
            if not isinstance(node, tuple):
                out[idx] = node
                continue
            j, k, left, right = node
            go = B[idx, j] <= k
            stack.append((left, idx[go]))
            stack.append((right, idx[~go]))
        return out

    def margin(self, X):
        B = self.encode(X)
        F = np.full(len(B), self.base)
        for tree in self.forest:
            F += self.lr * self._apply(tree, B)
        return F


def make_model(name, cfg, seed):
    return Logit(cfg["logit_l2"]) if name in ("M1", "M2") else GBDT(cfg, seed)


def training_sample(mask, y, cfg, rng):
    """Keep all positives; decimate negatives with weights that preserve the base rate."""
    idx = np.flatnonzero(mask & (y >= 0))
    neg = idx[y[idx] == 0]
    pos = idx[y[idx] == 1]
    rate = cfg["negative_keep_every"]
    kept = neg[rng.permutation(len(neg))[:len(neg) // rate]]
    chosen = np.sort(np.concatenate([pos, kept]))
    weights = np.where(y[chosen] == 1, 1.0, len(neg) / max(len(kept), 1))
    return chosen, weights


def fit_platt(margin, y):
    def objective(t):
        m = t[0] + t[1] * margin
        p = expit(m)
        return np.mean(np.logaddexp(0, m) - y * m), np.array([np.mean(p - y), np.mean((p - y) * margin)])
    prior = np.clip(y.mean(), 1e-7, 1 - 1e-7)
    start = np.array([np.log(prior / (1 - prior)), 0.0])
    r = minimize(objective, start, jac=True, method="L-BFGS-B", bounds=[(None, None), (0, None)])
    return r.x


def metrics(p, y):
    """Window-level descriptive metrics. Autocorrelated rows are not independent evidence."""
    out = {"windows": int(len(y)), "positives": int(y.sum()), "prevalence": float(y.mean()) if len(y) else None}
    if not len(y) or not y.sum() or y.all():
        return out
    order = np.argsort(-p, kind="stable")
    hits = y[order]
    precision = np.cumsum(hits) / np.arange(1, len(y) + 1)
    out["average_precision"] = float(np.sum(precision * hits) / hits.sum())
    ranks = np.empty(len(y))
    ranks[order] = np.arange(len(y), 0, -1)
    pos = y == 1
    out["auroc"] = float((ranks[pos].sum() - pos.sum() * (pos.sum() + 1) / 2) / (pos.sum() * (~pos).sum()))
    return out


def probability_metrics(p, y, reference):
    p = np.clip(p, 1e-7, 1 - 1e-7)
    if not len(y):
        return {}
    brier = float(np.mean((p - y) ** 2))
    base = float(np.mean((reference - y) ** 2))
    out = {"brier": brier, "brier_reference": base, "brier_skill": 1 - brier / base if base > 0 else None,
           "log_loss": float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))}
    if y.sum() and not y.all():
        logit = np.log(p / (1 - p))
        slope = fit_platt(logit, y)
        unconstrained = minimize(lambda t: (np.mean(np.logaddexp(0, t[0] + t[1] * logit) - y * (t[0] + t[1] * logit)),
                                            np.array([np.mean(expit(t[0] + t[1] * logit) - y),
                                                      np.mean((expit(t[0] + t[1] * logit) - y) * logit)])),
                                 slope, jac=True, method="L-BFGS-B")
        out["calibration_intercept"], out["calibration_slope"] = map(float, unconstrained.x)
    for bins in (5, 10, 15):
        split = np.array_split(np.argsort(p, kind="stable"), bins)
        out[f"ece_{bins}"] = float(sum(len(s) * abs(p[s].mean() - y[s].mean()) for s in split if len(s)) / len(y))
    top = np.argsort(-p, kind="stable")[:max(1, len(y) // 10)]
    out["top_decile_gap"] = float(abs(p[top].mean() - y[top].mean()))
    out["mean_predicted"], out["observed_rate"] = float(p.mean()), float(y.mean())
    return out


def alarm_series(score, threshold, valid, cfg):
    """Causal: m of k recent valid decisions above threshold, merged by a quiet period."""
    above = (score > threshold) & valid
    k, m = cfg["persist_window"], cfg["persist_required"]
    c = np.concatenate([[0], np.cumsum(above)])
    recent = c[1:] - c[np.maximum(np.arange(len(above)) + 1 - k, 0)]
    raw = (recent >= m) & valid
    alarms = np.zeros(len(raw), bool)
    last = -10 ** 9
    for t in np.flatnonzero(raw):
        if t - last >= cfg["alarm_merge_minutes"]:
            alarms[t] = True
            last = t
    return alarms, raw


def event_policy(score, threshold, valid, y, block, events_local, h, cfg, seed):
    """Report per-failure catches, alarm burden and a circular-shift chance rate."""
    alarms, raw = alarm_series(score, threshold, valid, cfg)
    lead_min = cfg["min_response_minutes"]
    idx = np.flatnonzero(block)
    a0, a1 = idx[0], idx[-1] + 1
    span = raw[a0:a1]
    per = {}
    rng = np.random.default_rng(seed)
    occupied = float(span.mean()) if len(span) else 0.0
    for key, onset in events_local:
        lo, hi = max(onset - h, a0), onset - lead_min
        if hi <= lo:
            per[key] = {"caught": False, "reason": "window_too_short"}
            continue
        window = raw[lo:hi]
        hits = np.flatnonzero(window)
        caught = bool(len(hits))
        shifted = 0
        length = a1 - a0
        offset = lo - a0
        width = hi - lo
        if length > width:
            c = np.concatenate([[0], np.cumsum(np.concatenate([span, span]))])
            shifts = rng.integers(1, length, cfg["circular_shifts"])
            starts = (offset - shifts) % length
            shifted = int(np.sum(c[starts + width] - c[starts] > 0))
        per[key] = {"caught": caught, "first_lead_minutes": int(onset - (lo + hits[0])) if caught else None,
                    "chance_rate_under_circular_shift": shifted / cfg["circular_shifts"]}
    scored = block & (y >= 0)
    false = int(np.sum(alarms & scored & (y == 0)))
    unscored = int(np.sum(alarms & block & (y < 0)))
    days = float(scored.sum()) / 1440
    return {"threshold": float(threshold), "failures": per, "false_alarm_episodes": false,
            "unscorable_alarm_episodes": unscored, "scored_days": days,
            "false_alarms_per_day": false / days if days else None, "alarm_occupancy": occupied}


# ---- Explanations -----------------------------------------------------------------------------

def family_groups(labels):
    groups = {}
    for family, members in FAMILIES.items():
        columns = [i for i, name in enumerate(labels) if name.split("|")[0] in members]
        if columns:
            groups[family] = columns
    return groups


def permutation_shap(model, rows, background, groups, draws, rng):
    """Interventional Shapley estimate on the log-odds margin, per sensor family."""
    names = list(groups)
    total = np.zeros((len(rows), len(names)))
    for r, row in enumerate(rows):
        batch, order_log = [], []
        for _ in range(draws):
            current = background[rng.integers(len(background))].copy()
            batch.append(current.copy())
            order = rng.permutation(len(names))
            for g in order:
                current[groups[names[g]]] = row[groups[names[g]]]
                batch.append(current.copy())
            order_log.append(order)
        output = model.margin(np.array(batch))
        pos = 0
        for order in order_log:
            prev = output[pos]
            pos += 1
            for g in order:
                total[r, g] += output[pos] - prev
                prev = output[pos]
                pos += 1
    return names, total / draws


def stability(a, b, k):
    a, b = np.asarray(a), np.asarray(b)
    ma, mb = np.abs(a).mean(axis=0), np.abs(b).mean(axis=0)
    rho = spearmanr(ma, mb).statistic
    ta, tb = set(np.argsort(-ma)[:k]), set(np.argsort(-mb)[:k])
    sa, sb = np.sign(a.mean(axis=0)), np.sign(b.mean(axis=0))
    denominator = np.linalg.norm(ma) * np.linalg.norm(mb)
    return {"spearman": None if np.isnan(rho) else float(rho), "top_k_jaccard": len(ta & tb) / len(ta | tb),
            "sign_agreement": float(np.mean(sa == sb)),
            "cosine": float(ma @ mb / denominator) if denominator else None}


# ---- Fold execution ---------------------------------------------------------------------------

STATE = {}


def init_worker(payload):
    STATE.update(payload)


def fit_predict(model_name, train_mask, score_masks, h, seed):
    cfg = STATE["cfg"]
    X = STATE["views"][model_name][0]
    y = STATE["y"][h]
    rng = np.random.default_rng(seed)
    idx, w = training_sample(train_mask & STATE["ok"], y, cfg, rng)
    if y[idx].sum() == 0:
        return None
    model = make_model(model_name, cfg, seed).fit(X[idx], y[idx].astype(float), w)
    return model, [model.margin(X[m]) for m in score_masks]


def run_fold(task):
    cfg, n, ranges = STATE["cfg"], STATE["n"], STATE["ranges"]
    fold, h, model_name = task["fold"], task["h"], task["model"]
    y, ok = STATE["y"][h], STATE["ok"]
    embargo = cfg["embargo_minutes"]
    if fold.get("test_after") is not None:
        test = np.zeros(n, bool)
        test[fold["test_after"]:] = True
    else:
        test = block_mask(n, ranges, fold["test"], embargo)
    train_all = block_mask(n, ranges, fold["train"], embargo)
    seed0 = cfg["seed"] + h + {"M1": 1, "M2": 2, "M3": 3, "M4": 4}[model_name]
    # Calibration scores never use the test block.
    oof_margin, oof_y = [], []
    if fold["mode"] == "cross_fit":
        for held in fold["train"]:
            rest = [b for b in fold["train"] if b != held]
            inner = block_mask(n, ranges, rest, embargo)
            hold = block_mask(n, ranges, [held], embargo) & ok & (y >= 0)
            fitted = fit_predict(model_name, inner, [hold], h, seed0)
            if fitted is None:
                continue
            oof_margin.append(fitted[1][0])
            oof_y.append(y[hold])
    else:
        hold = block_mask(n, ranges, fold["calibrate"], embargo) & ok & (y >= 0)
        fitted = fit_predict(model_name, train_all, [hold], h, seed0)
        if fitted is not None:
            oof_margin, oof_y = [fitted[1][0]], [y[hold]]
    if not oof_margin:
        return {"fold": fold["name"], "h": h, "model": model_name, "status": "no_positive_training_support"}
    oof_margin = np.concatenate(oof_margin)
    oof_y = np.concatenate(oof_y).astype(float)
    a, b = fit_platt(oof_margin, oof_y)
    threshold = float(np.quantile(oof_margin[oof_y == 0], cfg["alarm_quantile"]))
    train_prior = float(np.mean(y[train_all & ok & (y >= 0)] == 1))
    every = np.arange(n)[test]
    seeds = range(cfg["shap_seeds"]) if (model_name in cfg["shap_models"] and fold["kind"] == "A") else [0]
    result = {"fold": fold["name"], "kind": fold["kind"], "h": h, "model": model_name, "status": "done",
              "gate": "exploratory_descriptive_below_episode_gate", "train_prior": train_prior,
              "platt": [float(a), float(b)], "oof_windows": int(len(oof_y)), "oof_positive": int(oof_y.sum())}
    margin_full = None
    shap_store = {}
    for s in seeds:
        fitted = fit_predict(model_name, train_all, [test], h, seed0 + 1000 * s)
        if fitted is None:
            return {"fold": fold["name"], "h": h, "model": model_name, "status": "no_positive_training_support"}
        model, (margin,) = fitted
        if s == 0:
            margin_full = margin
        if model_name in cfg["shap_models"] and fold["kind"] == "A":
            X, labels = STATE["views"][model_name]
            common = np.flatnonzero(test & ok & (STATE["y"][cfg["horizon_minutes"][0]] == 1))
            step = max(1, len(common) // cfg["shap_rows"])
            common = common[::step][:cfg["shap_rows"]]
            normal = np.flatnonzero(train_all & ok & (y == 0))
            rng = np.random.default_rng(cfg["seed"] + 7 * h + s)
            background = X[rng.choice(normal, cfg["shap_background"], replace=False)]
            groups = family_groups(labels)
            names, values = permutation_shap(model, X[common], background, groups, cfg["shap_draws"], rng)
            shap_store[s] = {"families": names, "values": values.tolist()}
    margin = margin_full
    calibrated = expit(a + b * margin)
    raw = expit(margin)
    mask = ok[test] & (y[test] >= 0)
    labels = (y[test][mask] == 1).astype(float)
    reference = np.full(len(labels), train_prior)
    result["window"] = metrics(margin[mask], labels)
    result["uncalibrated"] = probability_metrics(raw[mask], labels, reference)
    result["platt_calibrated"] = probability_metrics(calibrated[mask], labels, reference)
    score = np.full(n, -np.inf)
    score[every] = margin
    valid = np.zeros(n, bool)
    valid[every] = ok[test]
    onsets = [(ev["id"], ev["onset"] - STATE["first"]) for ev in STATE["events"]
              if test[max(ev["onset"] - STATE["first"] - 1, 0)]]
    result["policy"] = event_policy(score, threshold, valid, y, test, onsets, h, cfg, cfg["seed"] + h)
    result["shap"] = shap_store
    per = {}
    ep = STATE["ep"][h]
    if len(onsets) > 1:
        for key, onset in onsets:
            k = [e["id"] for e in STATE["events"]].index(key)
            result.setdefault("episode_mean_probability", {})[key] = float(
                np.mean(calibrated[(ep[test] == k) & mask]))
    result["prediction_digest"] = hashlib.sha256(np.round(margin, 8).tobytes()).hexdigest()
    if task.get("store"):
        result["_scores"] = {"minute": every.tolist()[:0]}
    STATE_OUT = Path(STATE["out"]) / "scores"
    with gzip.open(STATE_OUT / f"{fold['name']}_h{h}_{model_name}.csv.gz", "wt", compresslevel=6) as s:
        s.write("minute_index,margin,platt,label\n")
        for i, m_, p_, l_ in zip(every, margin, calibrated, y[test]):
            if ok[i]:
                s.write(f"{i},{m_:.6f},{p_:.8f},{l_}\n")
    return result


def folds_for(n_events, ranges, events, first):
    assert n_events == 4
    items = []
    for t in range(4):
        items.append({"name": f"A_hold{events[t]['id']}", "kind": "A", "mode": "cross_fit", "test": [t],
                      "train": [b for b in range(4) if b != t]})
    items.append({"name": "B_hold_apr18", "kind": "B", "mode": "cross_fit", "test": [0], "train": [1, 2, 3]})
    items.append({"name": "B_hold_may29_jun05", "kind": "B", "mode": "cross_fit", "test": [1, 2], "train": [0, 3]})
    items.append({"name": "B_hold_jul15", "kind": "B", "mode": "cross_fit", "test": [3], "train": [0, 1, 2]})
    items.append({"name": "C_forward_jun05", "kind": "C", "mode": "single", "train": [0], "calibrate": [1],
                  "test": [2]})
    items.append({"name": "D_forward_jul15", "kind": "D", "mode": "single", "train": [0], "calibrate": [1, 2],
                  "test": [3]})
    items.append({"name": "E_false_alarm_after_jul16", "kind": "E", "mode": "cross_fit", "train": [0, 1, 2],
                  "test": [], "test_after": events[3]["release"] - first})
    return items


def read_events(path, cfg):
    events = []
    with open(path, newline="", encoding="utf-8") as stream:
        for row in csv.DictReader(stream):
            onset, end = epoch_minute(row["onset"]), epoch_minute(row["end"])
            release = epoch_minute(row["release"]) if row.get("release") else end + cfg["default_recovery_minutes"]
            events.append({"id": row["event_id"], "onset": onset, "end": end, "release": release})
    return sorted(events, key=lambda e: e["onset"])


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--csv", type=Path, required=True)
    cli.add_argument("--config", type=Path, required=True)
    cli.add_argument("--events", type=Path, required=True)
    cli.add_argument("--out", type=Path, required=True)
    cli.add_argument("--synthetic", action="store_true")
    cli.add_argument("--workers", type=int, default=6)
    args = cli.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "scores").mkdir()
    cfg = json.loads(args.config.read_text())
    events = read_events(args.events, cfg)
    data = load_minutes(args.csv)
    views, ok = features(data, cfg)
    y, ep, state = build_labels(data, events, cfg)
    n = len(data["grid"])
    ranges, _ = block_ranges(events, data["first"], n, cfg["embargo_minutes"])
    record = {"status": "running", "synthetic": args.synthetic, "python": platform.python_version(),
              "numpy": np.__version__, "platform": platform.platform(), "arguments": sys.argv[1:],
              "input": {"sha256": data["sha256"], "raw_rows": data["raw_rows"], "first": data["first_timestamp"],
                        "last": data["last_timestamp"], "access": "existing_file_author_exception"},
              "config": cfg, "config_sha256": digest(args.config), "events": events,
              "events_sha256": digest(args.events), "script_sha256": digest(__file__),
              "grid_minutes": n, "present_minutes": int(data["present"].sum()), "valid_decisions": int(ok.sum()),
              "blocks": ranges, "gates": {
                  "calibration_minimum_episodes": cfg["minimum_positive_episodes_for_calibration"],
                  "interval_minimum_episodes": cfg["minimum_positive_episodes_for_interval"],
                  "status": "failed_for_inferential_use: four reports; Platt results are exploratory and per failure"},
              "label_counts": {str(h): {"scored": int(((y[h] >= 0) & ok).sum()),
                                        "positive": int(((y[h] == 1) & ok).sum()),
                                        "per_event": [int((((ep[h] == k) & (y[h] == 1) & ok)).sum())
                                                      for k in range(len(events))]}
                               for h in cfg["horizon_minutes"]}}
    payload = {"cfg": cfg, "views": views, "ok": ok, "y": y, "ep": ep, "n": n, "ranges": ranges,
               "first": data["first"], "events": events, "out": str(args.out)}
    fold_items = folds_for(len(events), ranges, events, data["first"])
    tasks = [{"fold": f, "h": h, "model": m} for f in fold_items for h in cfg["horizon_minutes"]
             for m in cfg["models_by_fold"][f["kind"]]]
    record["tasks"] = len(tasks)
    print("tasks", len(tasks), flush=True)
    ctx = mp.get_context("fork")
    results = []
    with ctx.Pool(args.workers, initializer=init_worker, initargs=(payload,)) as pool:
        for i, r in enumerate(pool.imap_unordered(run_fold, tasks)):
            results.append(r)
            print(i + 1, r["fold"], r["h"], r["model"], r["status"], flush=True)
    results.sort(key=lambda r: (r["fold"], r["h"], r["model"]))
    record["results"] = results
    stable = {"across_seeds": [], "across_horizons": [], "across_failures": []}
    k = cfg["shap_top_k"]
    shap = {(r["fold"], r["h"], r["model"]): r["shap"] for r in results if r.get("shap")}
    for (fold, h, model), store in shap.items():
        for a, b in combinations(sorted(store), 2):
            stable["across_seeds"].append({"fold": fold, "h": h, "model": model, "pair": [a, b],
                                           **stability(store[a]["values"], store[b]["values"], k)})
    folds = sorted({key[0] for key in shap})
    models = sorted({key[2] for key in shap})
    for fold in folds:
        for model in models:
            for h1, h2 in combinations(cfg["horizon_minutes"], 2):
                if (fold, h1, model) in shap and (fold, h2, model) in shap:
                    stable["across_horizons"].append({
                        "fold": fold, "model": model, "pair": [h1, h2],
                        **stability(shap[(fold, h1, model)][0 if 0 in shap[(fold, h1, model)] else "0"]["values"],
                                    shap[(fold, h2, model)][0 if 0 in shap[(fold, h2, model)] else "0"]["values"], k)})
    for h in cfg["horizon_minutes"]:
        for model in models:
            for f1, f2 in combinations(folds, 2):
                if (f1, h, model) in shap and (f2, h, model) in shap:
                    stable["across_failures"].append({
                        "h": h, "model": model, "pair": [f1, f2],
                        **stability(shap[(f1, h, model)][0]["values"], shap[(f2, h, model)][0]["values"], k)})
    record["stability"] = stable
    record["status"] = "completed_with_gates"
    (args.out / "run.json").write_text(json.dumps(record, indent=1, allow_nan=False) + "\n")
    print("completed_with_gates", args.out / "run.json")


if __name__ == "__main__":
    sys.exit(main())
