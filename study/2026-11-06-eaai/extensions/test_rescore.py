"""Tests for tie-correct metrics, added after the tie bug was found."""
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import rescore


class Ties(unittest.TestCase):
    def test_all_tied_scores_give_chance_regardless_of_row_order(self):
        for y in (np.array([1., 1, 0, 0, 0, 0]), np.array([0., 0, 0, 0, 1, 1])):
            ap, auc = rescore.tie_metrics(np.zeros(6), y)
            self.assertAlmostEqual(auc, .5)
            self.assertAlmostEqual(ap, 2 / 6)

    def test_perfect_and_inverted(self):
        y = np.array([0., 0, 1, 1])
        self.assertAlmostEqual(rescore.tie_metrics(np.array([1., 2, 3, 4]), y)[1], 1)
        self.assertAlmostEqual(rescore.tie_metrics(np.array([4., 3, 2, 1]), y)[1], 0)
        self.assertAlmostEqual(rescore.tie_metrics(np.array([1., 2, 3, 4]), y)[0], 1)

    def test_known_auc_with_a_tie(self):
        self.assertAlmostEqual(rescore.tie_metrics(np.array([1., 2, 2, 3]), np.array([0., 0, 1, 1]))[1], .875)

    def test_ece_keeps_ties_together(self):
        p = np.r_[np.full(90, .1), np.full(10, .5)]
        y = np.r_[np.zeros(81), np.ones(9), np.ones(5), np.zeros(5)]
        self.assertAlmostEqual(rescore.tie_ece(p, y, 10), 0, places=9)


if __name__ == "__main__":
    unittest.main()
