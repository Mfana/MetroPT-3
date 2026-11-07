"""Sensitivity phases for M5 and M6 under provenance/registered-plan-addendum-gaps.md.

Reuses the frozen seq_study functions unchanged. One phase per process, because a second fork pool
in one process can crash on macOS. Finished tasks are kept in results.jsonl, so a stopped phase resumes.

Usage: .venv/bin/python -B seq_gaps.py --phase NAME --phases JSON --csv PATH --config CFG --base-config BASE
       --events EVENTS --out DIR --workers N
"""
import argparse
import hashlib
import json
import multiprocessing as mp
import platform
import sys
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent))
import event_study as es
import rescore
import seq_study as sq


def run_heldin(task):
    """Refit the final model of a fold and score its own training rows and its held-out block."""
    S = sq.STATE
    cfg, base, n, ranges = S["cfg"], S["base"], S["n"], S["ranges"]
    fold, h, name = task["fold"], task["h"], task["model"]
    y, ok, L, embargo = S["y"][h], S["ok"], base["lookback_minutes"], base["embargo_minutes"]
    grid, present = S["grid"], S["present"]
    seed = cfg["seed"] + h + {"M5": 5, "M6": 6}[name]
    index = np.arange(n)
    candidate = ok & (y >= 0) & (index >= L)
    mask = es.block_mask(n, ranges, fold["train"], embargo)
    mean, std = sq.scaling(grid, present, mask)
    tensor = torch.from_numpy(sq.standardized(grid, present, mean, std))
    model, rate = sq.fit(name, tensor, y, index[mask & candidate], cfg, L, seed)
    test = es.block_mask(n, ranges, fold["test"], embargo) & (index >= L)
    every = index[test & ok]
    margin = sq.score(model, tensor, every, L, rate, cfg)
    keep = y[every] >= 0
    ap_out, auroc_out = rescore.tie_metrics(margin[keep], (y[every][keep] == 1).astype(float))
    train = index[mask & candidate]
    train_margin = sq.score(model, tensor, train, L, rate, cfg)
    ap_in, auroc_in = rescore.tie_metrics(train_margin, (y[train] == 1).astype(float))
    full = np.full(n, np.nan)
    full[train] = train_margin
    per = {}
    for b in fold["train"]:
        rows = es.block_mask(n, ranges, [b], embargo) & mask & candidate
        ap_b, auroc_b = rescore.tie_metrics(full[rows], (y[rows] == 1).astype(float))
        per[S["events"][b]["id"]] = {"ap": ap_b, "auroc": auroc_b, "positives": int((y[rows] == 1).sum())}
    return {"fold": fold["name"], "h": h, "model": name, "status": "done", "train_windows": int(len(train)),
            "train_positives": int((y[train] == 1).sum()), "heldin_ap": ap_in, "heldin_auroc": auroc_in,
            "heldin_by_failure": per, "heldout_ap": ap_out, "heldout_auroc": auroc_out,
            "prediction_digest": hashlib.sha256(np.round(margin, 5).tobytes()).hexdigest()}


def run_task(task):
    return run_heldin(task) if task["mode"] == "heldin" else sq.run_fold(task)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--phase", required=True)
    for name in ("phases", "csv", "config", "base-config", "events", "out"):
        cli.add_argument("--" + name, type=Path, required=True)
    cli.add_argument("--workers", type=int, default=6)
    cli.add_argument("--synthetic", action="store_true")
    args = cli.parse_args()
    phase = json.loads(args.phases.read_text())[args.phase]
    (args.out / "scores").mkdir(parents=True, exist_ok=True)
    cfg = {**json.loads(args.config.read_text()), **phase["overrides"]}
    base = json.loads(args.base_config.read_text())
    events = es.read_events(args.events, base)
    data = es.load_minutes(args.csv)
    views, ok = es.features(data, base)
    del views
    y, _, _ = es.build_labels(data, events, base)
    n = len(data["grid"])
    ranges, _ = es.block_ranges(events, data["first"], n, base["embargo_minutes"])
    folds = {f["name"]: f for f in es.folds_for(len(events), ranges, events, data["first"])}
    done_path = args.out / "results.jsonl"
    results = [json.loads(line) for line in done_path.read_text().splitlines()] if done_path.exists() else []
    done = {(r["fold"], r["h"], r["model"]) for r in results}
    tasks = [{"fold": folds[f], "h": h, "model": m, "mode": phase["mode"]} for f in phase["folds"]
             for h in base["horizon_minutes"] for m in ("M5", "M6") if (f, h, m) not in done]
    print("phase", args.phase, "tasks", len(tasks), "already done", len(done), flush=True)
    payload = {"cfg": cfg, "base": base, "ok": ok, "y": y, "n": n, "ranges": ranges, "first": data["first"],
               "events": events, "out": str(args.out), "grid": data["grid"], "present": data["present"]}
    torch.set_num_threads(1)
    with mp.get_context("fork").Pool(args.workers, initializer=sq.init_worker, initargs=(payload,)) as pool, \
            done_path.open("a") as log:
        for i, r in enumerate(pool.imap_unordered(run_task, tasks)):
            results.append(r)
            log.write(json.dumps(r, allow_nan=False) + "\n")
            log.flush()
            print(i + 1, r["fold"], r["h"], r["model"], r["status"], flush=True)
    results.sort(key=lambda r: (r["fold"], r["h"], r["model"]))
    record = {"status": "completed_with_gates", "phase": args.phase, "mode": phase["mode"], "synthetic": args.synthetic,
              "python": platform.python_version(), "torch": torch.__version__, "numpy": np.__version__,
              "arguments": sys.argv[1:], "input": {"sha256": data["sha256"], "raw_rows": data["raw_rows"]},
              "config": cfg, "config_sha256": es.digest(args.config), "phases_sha256": es.digest(args.phases),
              "base_config_sha256": es.digest(args.base_config), "events_sha256": es.digest(args.events),
              "script_sha256": es.digest(__file__), "seq_study_sha256": es.digest(sq.__file__), "results": results}
    (args.out / "run.json").write_text(json.dumps(record, indent=1, allow_nan=False) + "\n")
    print("completed_with_gates", args.out / "run.json", flush=True)


if __name__ == "__main__":
    sys.exit(main())
