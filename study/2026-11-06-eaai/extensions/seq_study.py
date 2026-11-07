"""Sequence models under the same whole-failure folds as event_study.py. Registered by
provenance/registered-plan-addendum-sequence.md.

Usage: .venv/bin/python -B seq_study.py --csv PATH --config CFG --base-config BASE --events EVENTS --out NEW_DIR
"""
import argparse
import gzip
import hashlib
import json
import multiprocessing as mp
import platform
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import torch
from torch import nn

sys.path.insert(0, str(Path(__file__).parent))
import event_study as es
import rescore


class LSTMNet(nn.Module):
    def __init__(self, inputs, hidden, dropout):
        super().__init__()
        self.rnn = nn.LSTM(inputs, hidden, batch_first=True)
        self.drop = nn.Dropout(dropout)
        self.head = nn.Linear(hidden, 1)

    def forward(self, x):
        out, _ = self.rnn(x)
        return self.head(self.drop(out[:, -1])).squeeze(-1)


class CausalBlock(nn.Module):
    def __init__(self, inputs, channels, kernel, dilation, dropout):
        super().__init__()
        self.left = (kernel - 1) * dilation
        self.conv = nn.Conv1d(inputs, channels, kernel, dilation=dilation)
        self.drop = nn.Dropout(dropout)
        self.skip = nn.Conv1d(inputs, channels, 1) if inputs != channels else nn.Identity()

    def forward(self, x):
        y = nn.functional.pad(x, (self.left, 0))
        return self.drop(torch.relu(self.conv(y))) + self.skip(x)


class TCNNet(nn.Module):
    def __init__(self, inputs, channels, kernel, dilations, dropout):
        super().__init__()
        layers, width = [], inputs
        for d in dilations:
            layers.append(CausalBlock(width, channels, kernel, d, dropout))
            width = channels
        self.body = nn.Sequential(*layers)
        self.head = nn.Linear(channels, 1)

    def forward(self, x):
        return self.head(self.body(x.transpose(1, 2))[:, :, -1]).squeeze(-1)


def build(name, cfg, inputs):
    if name == "M5":
        return LSTMNet(inputs, cfg["hidden"], cfg["dropout"])
    return TCNNet(inputs, cfg["hidden"], cfg["kernel"], cfg["dilations"], cfg["dropout"])


def scaling(grid, present, mask):
    """Fit channel location and scale on training minutes only."""
    use = mask & present
    mean = np.nanmean(grid[use], axis=0)
    std = np.nanstd(grid[use], axis=0)
    std[std < 1e-6] = 1.0
    return mean, std


def standardized(grid, present, mean, std):
    """Missing minutes become 0 with an explicit observed-channel flag. No future values are used."""
    z = np.where(present[:, None], (grid - mean) / std, 0.0)
    z = np.nan_to_num(z, nan=0.0)
    return np.concatenate([z, present[:, None].astype(float)], axis=1).astype(np.float32)


def windows(tensor, index, L):
    """Rows t-L to t-1 for each decision t. The row at t is never included."""
    offsets = torch.arange(-L, 0)
    return tensor[torch.as_tensor(index)[:, None] + offsets]


def prior_correct(logit, sample_rate, base_rate):
    """Map balanced-batch log-odds back to the true base rate."""
    shift = np.log(base_rate / (1 - base_rate)) - np.log(sample_rate / (1 - sample_rate))
    return logit + shift


def fit(name, tensor, y, train_idx, cfg, L, seed):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    positives = train_idx[y[train_idx] == 1]
    negatives = train_idx[y[train_idx] == 0]
    if not len(positives):
        return None
    model = build(name, cfg, tensor.shape[1])
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg["learning_rate"], weight_decay=cfg["weight_decay"])
    size, share = cfg["batch_size"], cfg["positive_share"]
    n_pos = int(size * share)
    model.train()
    for _ in range(cfg["train_steps"]):
        batch = np.concatenate([rng.choice(positives, n_pos), rng.choice(negatives, size - n_pos)])
        target = torch.tensor(np.r_[np.ones(n_pos), np.zeros(size - n_pos)], dtype=torch.float32)
        loss = nn.functional.binary_cross_entropy_with_logits(model(windows(tensor, batch, L)), target)
        optimizer.zero_grad()
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
    model.eval()
    return model, len(positives) / len(train_idx)


@torch.no_grad()
def score(model, tensor, index, L, base_rate, cfg):
    out = []
    for start in range(0, len(index), cfg["score_batch"]):
        out.append(model(windows(tensor, index[start:start + cfg["score_batch"]], L)).numpy())
    logit = np.concatenate(out).astype(np.float64) if out else np.array([])
    return prior_correct(logit, cfg["positive_share"], base_rate)


STATE = {}


def init_worker(payload):
    STATE.update(payload)
    torch.set_num_threads(payload["cfg"]["torch_threads"])


def run_fold(task):
    cfg, n = STATE["cfg"], STATE["n"]
    base, ranges = STATE["base"], STATE["ranges"]
    fold, h, name = task["fold"], task["h"], task["model"]
    y, ok, L = STATE["y"][h], STATE["ok"], base["lookback_minutes"]
    grid, present = STATE["grid"], STATE["present"]
    embargo = base["embargo_minutes"]
    seed = cfg["seed"] + h + {"M5": 5, "M6": 6}[name]
    index = np.arange(n)
    candidate = ok & (y >= 0) & (index >= L)

    def train_and_score(train_blocks, score_mask):
        mask = es.block_mask(n, ranges, train_blocks, embargo)
        mean, std = scaling(grid, present, mask)
        tensor = torch.from_numpy(standardized(grid, present, mean, std))
        result = fit(name, tensor, y, index[mask & candidate], cfg, L, seed)
        if result is None:
            return None
        model, rate = result
        return model, tensor, rate, score(model, tensor, index[score_mask], L, rate, cfg)

    oof_margin, oof_y = [], []
    if fold["mode"] == "cross_fit":
        for held in fold["train"]:
            rest = [b for b in fold["train"] if b != held]
            hold = es.block_mask(n, ranges, [held], embargo) & candidate
            done = train_and_score(rest, hold)
            if done is None:
                continue
            oof_margin.append(done[3])
            oof_y.append(y[hold])
    else:
        hold = es.block_mask(n, ranges, fold["calibrate"], embargo) & candidate
        done = train_and_score(fold["train"], hold)
        if done is not None:
            oof_margin, oof_y = [done[3]], [y[hold]]
    if not oof_margin:
        return {"fold": fold["name"], "h": h, "model": name, "status": "no_positive_training_support"}
    oof_margin = np.concatenate(oof_margin)
    oof_y = np.concatenate(oof_y).astype(float)
    a, b = es.fit_platt(oof_margin, oof_y)
    threshold = float(np.quantile(oof_margin[oof_y == 0], base["alarm_quantile"]))
    if fold.get("test_after") is not None:
        test = np.zeros(n, bool)
        test[fold["test_after"]:] = True
    else:
        test = es.block_mask(n, ranges, fold["test"], embargo)
    test &= index >= L
    done = train_and_score(fold["train"], test & ok)
    if done is None:
        return {"fold": fold["name"], "h": h, "model": name, "status": "no_positive_training_support"}
    _, _, rate, margin_ok = done
    every = index[test & ok]
    mask = y[every] >= 0
    labels = (y[every][mask] == 1).astype(float)
    calibrated = 1 / (1 + np.exp(-(a + b * margin_ok)))
    raw = 1 / (1 + np.exp(-margin_ok))
    reference = np.full(len(labels), rate)
    result = {"fold": fold["name"], "kind": fold["kind"], "h": h, "model": name, "status": "done",
              "gate": "exploratory_descriptive_below_episode_gate", "train_prior": rate,
              "platt": [float(a), float(b)], "oof_windows": len(oof_y), "oof_positive": int(oof_y.sum())}
    ap, auroc = rescore.tie_metrics(margin_ok[mask], labels) if len(labels) else (None, None)
    result["window"] = {"windows": int(len(labels)), "positives": int(labels.sum()),
                        "prevalence": float(labels.mean()) if len(labels) else None,
                        "average_precision": ap, "auroc": auroc, "distinct_scores": int(len(np.unique(margin_ok[mask])))}
    result["uncalibrated"] = es.probability_metrics(raw[mask], labels, reference)
    result["platt_calibrated"] = es.probability_metrics(calibrated[mask], labels, reference)
    full = np.full(n, -np.inf)
    full[every] = margin_ok
    valid = np.zeros(n, bool)
    valid[every] = True
    first = STATE["first"]
    onsets = [(e["id"], e["onset"] - first) for e in STATE["events"] if test[max(e["onset"] - first - 1, 0)]]
    result["policy"] = es.event_policy(full, threshold, valid, y, test, onsets, h, base, cfg["seed"] + h)
    result["prediction_digest"] = hashlib.sha256(np.round(margin_ok, 5).tobytes()).hexdigest()
    with gzip.open(Path(STATE["out"]) / "scores" / f"{fold['name']}_h{h}_{name}.csv.gz", "wt", compresslevel=6) as s:
        s.write("minute_index,margin,platt,label\n")
        for i, m_, p_ in zip(every, margin_ok, calibrated):
            s.write(f"{i},{m_:.6f},{p_:.8f},{y[i]}\n")
    return result


def run_random(task):
    """Exploratory row-random split, added to show how much the split alone changes the score."""
    cfg, n, base = STATE["cfg"], STATE["n"], STATE["base"]
    h, name = task["h"], task["model"]
    y, ok, L = STATE["y"][h], STATE["ok"], base["lookback_minutes"]
    grid, present = STATE["grid"], STATE["present"]
    seed = cfg["seed"] + h + 50
    rng = np.random.default_rng(seed)
    index = np.arange(n)
    valid = ok & (y >= 0) & (index >= L)
    train = valid & (rng.random(n) < .6)
    test = valid & ~train
    mean, std = scaling(grid, present, train)
    tensor = torch.from_numpy(standardized(grid, present, mean, std))
    model, rate = fit(name, tensor, y, index[train], cfg, L, seed)
    margin = score(model, tensor, index[test], L, rate, cfg)
    t = (y[test] == 1).astype(float)
    ap, auroc = rescore.tie_metrics(margin, t)
    return {"fold": "random_split", "kind": "exploratory", "h": h, "model": name, "status": "done",
            "window": {"windows": int(test.sum()), "positives": int(t.sum()), "prevalence": float(t.mean()),
                       "average_precision": ap, "auroc": auroc}}


def run_task(task):
    if task.get("random"):
        return run_random(task)
    return run_fold(task)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("csv", "config", "base-config", "events", "out"):
        cli.add_argument("--" + name, type=Path, required=True)
    cli.add_argument("--synthetic", action="store_true")
    cli.add_argument("--workers", type=int, default=3)
    cli.add_argument("--only-fold")
    args = cli.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out / "scores").mkdir()
    cfg = json.loads(args.config.read_text())
    base = json.loads(args.base_config.read_text())
    events = es.read_events(args.events, base)
    data = es.load_minutes(args.csv)
    views, ok = es.features(data, base)
    del views
    y, _, _ = es.build_labels(data, events, base)
    n = len(data["grid"])
    ranges, _ = es.block_ranges(events, data["first"], n, base["embargo_minutes"])
    folds = es.folds_for(len(events), ranges, events, data["first"])
    tasks = [{"fold": f, "h": h, "model": m} for f in folds for h in base["horizon_minutes"]
             for m in cfg["models_by_fold"].get(f["kind"], [])
             if not args.only_fold or args.only_fold == f["name"]]
    if not args.only_fold:
        tasks += [{"random": True, "h": h, "model": cfg["random_split_model"]} for h in base["horizon_minutes"]]
    print("tasks", len(tasks), flush=True)
    payload = {"cfg": cfg, "base": base, "ok": ok, "y": y, "n": n, "ranges": ranges, "first": data["first"],
               "events": events, "out": str(args.out), "grid": data["grid"], "present": data["present"]}
    torch.set_num_threads(1)
    results = []
    with mp.get_context("fork").Pool(args.workers, initializer=init_worker, initargs=(payload,)) as pool:
        for i, r in enumerate(pool.imap_unordered(run_task, tasks)):
            results.append(r)
            print(i + 1, r["fold"], r["h"], r["model"], r["status"], datetime.now().strftime("%H:%M:%S"), flush=True)
    results.sort(key=lambda r: (r["fold"], r["h"], r["model"]))
    record = {"status": "completed_with_gates", "synthetic": args.synthetic, "python": platform.python_version(),
              "torch": torch.__version__, "numpy": np.__version__, "arguments": sys.argv[1:],
              "input": {"sha256": data["sha256"], "raw_rows": data["raw_rows"]},
              "config": cfg, "config_sha256": es.digest(args.config), "base_config_sha256": es.digest(args.base_config),
              "events_sha256": es.digest(args.events), "script_sha256": es.digest(__file__),
              "gates": {"calibration_minimum_episodes": base["minimum_positive_episodes_for_calibration"],
                        "status": "failed_for_inferential_use: four reports; results exploratory and per failure"},
              "results": results}
    (args.out / "run.json").write_text(json.dumps(record, indent=1, allow_nan=False) + "\n")
    print("completed_with_gates", args.out / "run.json")


if __name__ == "__main__":
    sys.exit(main())
