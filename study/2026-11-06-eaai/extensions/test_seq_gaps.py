"""Synthetic tests: held-in refit reproduces the frozen pipeline, phases resume, shifted labels follow the onset."""
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import event_study as es
import seq_gaps
from test_event_study import CONFIG
from test_seq_study import SEQ


def make(root, shift=0):
    names = es.ANALOG + es.DIGITAL
    start = datetime(2020, 1, 1)
    rng = np.random.default_rng(2)
    onsets = [start + timedelta(days=d) for d in (3, 6, 9, 12)]
    with (root / "x.csv").open("w", newline="") as s:
        w = csv.writer(s)
        w.writerow(["timestamp", *names])
        for i in range(15 * 1440):
            t = start + timedelta(minutes=i)
            row = rng.normal(size=len(names)).round(3).tolist()
            row[names.index("COMP")] = int(rng.random() < .8)
            if any(timedelta(0) <= o - t <= timedelta(hours=1) for o in onsets):
                row[0] += 6
            w.writerow([t.isoformat(sep=" "), *row])
    with (root / "e.csv").open("w", newline="") as s:
        w = csv.writer(s)
        w.writerow(["event_id", "onset", "end", "release"])
        for k, o in enumerate(onsets):
            w.writerow([f"e{k}", (o + timedelta(minutes=shift)).isoformat(), (o + timedelta(hours=2)).isoformat(),
                        (o + timedelta(hours=8)).isoformat()])
    (root / "b.json").write_text(json.dumps({**CONFIG, "embargo_minutes": 120}))
    (root / "c.json").write_text(json.dumps({**SEQ, "torch_threads": 1}))
    (root / "p.json").write_text(json.dumps({
        "fit": {"mode": "full", "overrides": {}, "folds": ["A_holde1"]},
        "in": {"mode": "heldin", "overrides": {}, "folds": ["A_holde1"]}}))


def run(root, phase, out):
    return subprocess.run([sys.executable, "-B", seq_gaps.__file__, "--phase", phase, "--phases", str(root / "p.json"),
                           "--csv", str(root / "x.csv"), "--config", str(root / "c.json"), "--base-config",
                           str(root / "b.json"), "--events", str(root / "e.csv"), "--out", str(root / out),
                           "--synthetic", "--workers", "1"], check=True, capture_output=True, text=True)


class Tests(unittest.TestCase):
    def test_heldin_reproduces_digest_and_resume_skips_done_tasks(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make(root)
            run(root, "fit", "fit")
            run(root, "in", "in")
            full = json.loads((root / "fit/run.json").read_text())["results"]
            held = json.loads((root / "in/run.json").read_text())["results"]
            key = lambda r: (r["fold"], r["h"], r["model"])
            self.assertEqual({key(r): r["prediction_digest"] for r in full},
                             {key(r): r["prediction_digest"] for r in held})
            for r in held:
                self.assertEqual(len(r["heldin_by_failure"]), 3)
                self.assertGreater(r["train_positives"], 0)
            out = run(root, "in", "in").stdout
            self.assertIn("tasks 0 ", out)
            self.assertEqual(len(json.loads((root / "in/run.json").read_text())["results"]), len(held))

    def test_shifted_onset_moves_labels_and_exclusions(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            make(root, 0)
            data = es.load_minutes(root / "x.csv")
            base = {**CONFIG, "embargo_minutes": 120}
            y0, _, _ = es.build_labels(data, es.read_events(root / "e.csv", base), base)
            make(root, 60)
            y1, _, _ = es.build_labels(data, es.read_events(root / "e.csv", base), base)
            h = base["horizon_minutes"][0]
            first = np.flatnonzero(y0[h] == 1)[0]
            self.assertEqual(np.flatnonzero(y1[h] == 1)[0], first + 60)
            onset = first + h
            self.assertEqual(y0[h][onset + 30], -1)
            self.assertEqual(y1[h][onset + 30], 1 if h >= 30 else 0)


if __name__ == "__main__":
    unittest.main()
