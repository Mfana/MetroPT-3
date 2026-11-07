"""Synthetic tests for leakage, labels, alarms, explanations and the fold plan."""
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

CONFIG = {"lookback_minutes": 60, "delta_edge_minutes": 10, "state_history_minutes": 360, "min_lookback_coverage": .7,
          "min_followup_coverage": .5, "horizon_minutes": [30, 60], "default_recovery_minutes": 1440,
          "embargo_minutes": 780, "negative_keep_every": 5, "logit_l2": 1e-3, "gbdt_trees": 15,
          "gbdt_learning_rate": .1, "gbdt_depth": 2, "gbdt_min_hessian": 2.0, "gbdt_bins": 16, "gbdt_l2": 1.0,
          "gbdt_subsample": .8, "seed": 5, "alarm_quantile": .995, "persist_window": 5, "persist_required": 3,
          "alarm_merge_minutes": 60, "min_response_minutes": 5, "circular_shifts": 50, "shap_models": ["M3"],
          "shap_seeds": 2, "shap_rows": 4, "shap_background": 8, "shap_draws": 2, "shap_top_k": 3,
          "minimum_positive_episodes_for_calibration": 5, "minimum_positive_episodes_for_interval": 10,
          "models_by_fold": {"A": ["M1", "M3"], "B": ["M1"], "C": ["M1"], "D": ["M1"], "E": ["M1"]}}


def fake_data(n=3000):
    names = es.ANALOG + es.DIGITAL
    rng = np.random.default_rng(1)
    grid = rng.normal(size=(n, len(names)))
    grid[:, names.index("COMP")] = rng.integers(0, 2, n)
    return {"first": 0, "grid": grid, "present": np.ones(n, bool), "names": names}


class Tests(unittest.TestCase):
    def test_features_ignore_the_future(self):
        data = fake_data()
        before, ok = es.features(data, CONFIG)
        t = 1500
        data2 = {**data, "grid": data["grid"].copy()}
        data2["grid"][t:] += 50.0
        after, _ = es.features(data2, CONFIG)
        for key in before:
            a, b = before[key][0][:t + 1], after[key][0][:t + 1]
            self.assertTrue(np.array_equal(np.nan_to_num(a), np.nan_to_num(b)), key)

    def test_labels_and_exclusions(self):
        data = fake_data()
        events = [{"id": "e", "onset": 1000, "end": 1100, "release": 1300}]
        y, ep, _ = es.build_labels(data, events, CONFIG)
        self.assertEqual(y[30][969], 0)
        self.assertEqual(y[30][970], 1)
        self.assertEqual(y[30][999], 1)
        self.assertEqual(y[30][1000], -1)
        self.assertEqual(y[30][1299], -1)
        self.assertEqual(y[30][1300], 0)
        self.assertEqual(y[60][940], 1)

    def test_gap_censors_negatives_not_positives(self):
        data = fake_data()
        data["present"][800:1000] = False
        events = [{"id": "e", "onset": 1000, "end": 1010, "release": 1100}]
        y, _, _ = es.build_labels(data, events, CONFIG)
        self.assertEqual(y[30][750], 0)
        self.assertEqual(y[30][795], -1)  # Next 30 minutes mostly missing, so its outcome is unknown.
        data2 = fake_data()
        data2["present"][990:1000] = False
        y2, _, _ = es.build_labels(data2, events, CONFIG)
        self.assertEqual(y2[30][985], 1)

    def test_embargo_keeps_blocks_apart(self):
        events = [{"id": str(i), "onset": a, "end": a + 10, "release": a + 20} for i, a in
                  enumerate((1000, 5000, 9000, 13000))]
        ranges, _ = es.block_ranges(events, 0, 16000, 780)
        one, two = es.block_mask(16000, ranges, [0], 780), es.block_mask(16000, ranges, [1], 780)
        self.assertFalse((one & two).any())
        self.assertGreaterEqual(np.flatnonzero(two)[0] - np.flatnonzero(one)[-1], 2 * 780)

    def test_training_weights_keep_the_base_rate(self):
        y = np.zeros(10000, np.int8)
        y[:100] = 1
        idx, w = es.training_sample(np.ones(10000, bool), y, CONFIG, np.random.default_rng(0))
        self.assertAlmostEqual(np.average(y[idx], weights=w), .01, places=6)

    def test_gbdt_and_logit_learn(self):
        rng = np.random.default_rng(0)
        X = rng.normal(size=(4000, 4))
        y = (X[:, 1] > 1).astype(float)
        for model in (es.GBDT(CONFIG, 0), es.Logit(1e-3)):
            model.fit(X, y, np.ones(4000))
            m = model.metrics if False else model.margin(X)
            self.assertGreater(es.metrics(m, y)["auroc"], .95)

    def test_gbdt_handles_nan_and_is_deterministic(self):
        rng = np.random.default_rng(0)
        X = rng.normal(size=(1000, 3))
        X[::4, 0] = np.nan
        y = np.isnan(X[:, 0]).astype(float)
        a = es.GBDT(CONFIG, 3).fit(X, y, np.ones(1000)).margin(X)
        b = es.GBDT(CONFIG, 3).fit(X, y, np.ones(1000)).margin(X)
        self.assertTrue(np.array_equal(a, b))
        self.assertGreater(es.metrics(a, y)["auroc"], .99)

    def test_platt_recovers_a_scale(self):
        rng = np.random.default_rng(0)
        m = rng.normal(size=50000)
        y = (rng.random(50000) < 1 / (1 + np.exp(-(1 + 2 * m)))).astype(float)
        a, b = es.fit_platt(m, y)
        self.assertAlmostEqual(a, 1, delta=.1)
        self.assertAlmostEqual(b, 2, delta=.1)

    def test_probability_metrics_perfect_calibration_near_zero(self):
        rng = np.random.default_rng(0)
        p = rng.uniform(.01, .9, 100000)
        y = (rng.random(100000) < p).astype(float)
        out = es.probability_metrics(p, y, np.full(100000, y.mean()))
        self.assertLess(out["ece_10"], .01)
        self.assertAlmostEqual(out["calibration_slope"], 1, delta=.05)
        self.assertGreater(out["brier_skill"], 0)

    def test_alarm_persistence_and_merging(self):
        cfg = {"persist_window": 5, "persist_required": 3, "alarm_merge_minutes": 60}
        score = np.zeros(200)
        score[[10, 12, 14]] = 1
        score[[100, 101, 102]] = 1
        alarms, _ = es.alarm_series(score, .5, np.ones(200, bool), cfg)
        self.assertEqual(list(np.flatnonzero(alarms)), [14, 102])
        lone = np.zeros(50)
        lone[[10, 20, 30]] = 1
        self.assertFalse(es.alarm_series(lone, .5, np.ones(50, bool), cfg)[0].any())

    def test_circular_shift_rate_tracks_occupancy(self):
        cfg = {"persist_window": 1, "persist_required": 1, "alarm_merge_minutes": 1, "min_response_minutes": 0,
               "circular_shifts": 2000}
        n = 10000
        score = (np.arange(n) % 100 == 0).astype(float)  # One alarm every 100 minutes.
        y = np.zeros(n, np.int8)
        result = es.event_policy(score, .5, np.ones(n, bool), y, np.ones(n, bool), [("e", 5000)], 100, cfg, 1)
        self.assertGreater(result["failures"]["e"]["chance_rate_under_circular_shift"], .95)
        rare = np.zeros(n)
        rare[5] = 1
        out = es.event_policy(rare, .5, np.ones(n, bool), y, np.ones(n, bool), [("e", 5000)], 100, cfg, 1)
        self.assertLess(out["failures"]["e"]["chance_rate_under_circular_shift"], .05)

    def test_shapley_is_additive_for_a_linear_model(self):
        class Linear:
            def margin(self, X):
                return X @ np.array([1.0, -2.0, 3.0])
        rows = np.array([[1.0, 1.0, 1.0], [2.0, 0.0, -1.0]])
        background = np.zeros((4, 3))
        names, values = es.permutation_shap(Linear(), rows, background, {"a": [0], "b": [1], "c": [2]}, 3,
                                            np.random.default_rng(0))
        self.assertTrue(np.allclose(values[0], [1, -2, 3]))
        self.assertTrue(np.allclose(values.sum(axis=1), Linear().margin(rows)))

    def test_fold_plan_never_trains_on_test_block(self):
        events = [{"id": str(i), "onset": i * 100, "end": i * 100 + 1, "release": i * 100 + 2} for i in range(4)]
        for fold in es.folds_for(4, None, events, 0):
            used = set(fold["train"]) | set(fold.get("calibrate", []))
            self.assertFalse(used & set(fold["test"]), fold["name"])
            if fold["kind"] in "CD":
                self.assertLess(max(used), min(fold["test"]), fold["name"])

    def test_end_to_end_on_synthetic_telemetry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            names = es.ANALOG + es.DIGITAL
            start = datetime(2020, 1, 1)
            rng = np.random.default_rng(2)
            onsets = [start + timedelta(days=d) for d in (6, 12, 18, 24)]
            with (root / "x.csv").open("w", newline="") as s:
                w = csv.writer(s)
                w.writerow(["timestamp", *names])
                for i in range(30 * 1440):
                    t = start + timedelta(minutes=i)
                    near = any(timedelta(0) <= o - t <= timedelta(hours=1) for o in onsets)
                    row = rng.normal(size=len(names)).round(3).tolist()
                    row[names.index("COMP")] = int(rng.random() < .8)
                    if near:
                        row[0] += 6
                    w.writerow([t.isoformat(sep=" "), *row])
            with (root / "e.csv").open("w", newline="") as s:
                w = csv.writer(s)
                w.writerow(["event_id", "onset", "end", "release"])
                for k, o in enumerate(onsets):
                    w.writerow([f"e{k}", o.isoformat(), (o + timedelta(hours=2)).isoformat(),
                                (o + timedelta(hours=8)).isoformat()])
            (root / "c.json").write_text(json.dumps(CONFIG))
            for name in ("one", "two"):
                subprocess.run([sys.executable, "-B", es.__file__, "--csv", str(root / "x.csv"), "--config",
                                str(root / "c.json"), "--events", str(root / "e.csv"), "--out", str(root / name),
                                "--synthetic", "--workers", "2"], check=True, capture_output=True)
            a = json.loads((root / "one/run.json").read_text())
            b = json.loads((root / "two/run.json").read_text())
            self.assertEqual(a["status"], "completed_with_gates")
            self.assertTrue(a["synthetic"])
            self.assertEqual([r.get("prediction_digest") for r in a["results"]],
                             [r.get("prediction_digest") for r in b["results"]])
            hits = [r for r in a["results"] if r["fold"] == "A_holde1" and r["h"] == 60 and r["model"] == "M3"][0]
            self.assertGreater(hits["window"]["average_precision"], .5)


if __name__ == "__main__":
    unittest.main()
