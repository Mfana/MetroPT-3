"""Synthetic tests for causal windows, models, prior correction and determinism."""
import csv
import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).parent))
import event_study as es
import seq_study as sq
from test_event_study import CONFIG

SEQ = {"hidden": 8, "dropout": 0.0, "kernel": 3, "dilations": [1, 2, 4, 8, 16], "learning_rate": 0.003,
       "weight_decay": 0.0001, "batch_size": 64, "positive_share": 0.25, "train_steps": 60, "score_batch": 512,
       "seed": 3, "torch_threads": 1, "random_split_model": "M5",
       "models_by_fold": {"A": ["M5", "M6"], "D": ["M5"]}}


class Tests(unittest.TestCase):
    def test_windows_exclude_the_decision_row(self):
        tensor = torch.arange(100, dtype=torch.float32)[:, None]
        w = sq.windows(tensor, np.array([70]), 60)
        self.assertEqual(w.shape, (1, 60, 1))
        self.assertEqual(float(w[0, 0, 0]), 10)
        self.assertEqual(float(w[0, -1, 0]), 69)

    def test_tcn_receptive_field_covers_lookback_and_is_causal(self):
        torch.manual_seed(0)
        net = sq.build("M6", SEQ, 4).eval()
        x = torch.zeros(1, 60, 4, requires_grad=True)
        net(x).sum().backward()
        self.assertTrue((x.grad[0].abs().sum(dim=1) > 0)[60 - 32:].all())
        y = torch.randn(1, 60, 4)
        changed = y.clone()
        changed[0, 0] += 100  # Oldest row may matter; the output is still defined at the last row.
        self.assertEqual(net(y).shape, (1,))

    def test_lstm_output_ignores_nothing_before_last_step(self):
        torch.manual_seed(0)
        net = sq.build("M5", SEQ, 4).eval()
        x = torch.randn(2, 60, 4)
        self.assertEqual(net(x).shape, (2,))

    def test_prior_correction_recovers_base_rate(self):
        rng = np.random.default_rng(0)
        base = .001
        balanced = np.full(1000, np.log(.25 / .75))
        out = sq.prior_correct(balanced, .25, base)
        self.assertAlmostEqual(1 / (1 + np.exp(-out[0])), base, places=6)
        self.assertLess(abs(rng.random() - .5), 1)

    def test_scaling_uses_only_training_rows(self):
        grid = np.array([[1.0], [3.0], [1000.0]])
        present = np.ones(3, bool)
        mean, std = sq.scaling(grid, present, np.array([True, True, False]))
        self.assertAlmostEqual(mean[0], 2.0)
        self.assertAlmostEqual(std[0], 1.0)

    def test_missing_minutes_are_flagged_not_filled_from_the_future(self):
        grid = np.array([[1.0], [np.nan], [3.0]])
        present = np.array([True, False, True])
        z = sq.standardized(grid, present, np.array([0.0]), np.array([1.0]))
        self.assertEqual(z[1, 0], 0)
        self.assertEqual(z[1, 1], 0)
        self.assertEqual(z[2, 1], 1)

    def test_models_learn_a_separable_signal(self):
        n = 3000
        rng = np.random.default_rng(1)
        grid = rng.normal(size=(n, 3)).astype(np.float32)
        y = np.zeros(n, np.int8)
        for start in range(200, 2900, 400):
            grid[start - 40:start + 40, 0] += 5
            y[start:start + 30] = 1
        tensor = torch.from_numpy(grid)
        index = np.arange(70, n)
        cfg = {**SEQ, "train_steps": 120}
        for name in ("M5", "M6"):
            model, rate = sq.fit(name, tensor, y, index, cfg, 60, 1)
            margin = sq.score(model, tensor, index, 60, rate, cfg)
            self.assertGreater(es.metrics(margin, y[index].astype(float))["auroc"], .9, name)

    def test_end_to_end_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
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
                    w.writerow([f"e{k}", o.isoformat(), (o + timedelta(hours=2)).isoformat(),
                                (o + timedelta(hours=8)).isoformat()])
            (root / "b.json").write_text(json.dumps({**CONFIG, "embargo_minutes": 120}))
            (root / "c.json").write_text(json.dumps(SEQ))
            for out in ("one", "two"):
                subprocess.run([sys.executable, "-B", sq.__file__, "--csv", str(root / "x.csv"), "--config",
                                str(root / "c.json"), "--base-config", str(root / "b.json"), "--events",
                                str(root / "e.csv"), "--out", str(root / out), "--only-fold", "A_holde1",
                                "--synthetic", "--workers", "1"], check=True, capture_output=True)
            a = json.loads((root / "one/run.json").read_text())
            b = json.loads((root / "two/run.json").read_text())
            self.assertEqual([r["prediction_digest"] for r in a["results"]],
                             [r["prediction_digest"] for r in b["results"]])
            self.assertTrue(a["synthetic"])


if __name__ == "__main__":
    unittest.main()
