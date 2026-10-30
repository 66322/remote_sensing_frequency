import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from eval_rebuild_v1_b3_paired_regions import paired_outcomes


class PairedDiagnosticTests(unittest.TestCase):
    def test_transition_partition_and_ignore(self):
        gt = np.array([[0, 1, 2], [3, 4, 255]])
        clean = np.array([[0, 0, 2], [1, 4, 0]])
        corrupt = np.array([[1, 1, 2], [3, 0, 5]])
        mask = np.ones_like(gt, dtype=bool)
        out = paired_outcomes(gt, clean, corrupt, mask)
        self.assertEqual(out["valid_pixels"], 5)
        self.assertEqual(out["clean_correct_corrupt_wrong"], 2)
        self.assertEqual(out["clean_wrong_corrupt_correct"], 2)
        self.assertEqual(out["both_correct"], 1)
        self.assertEqual(out["both_wrong"], 0)
        self.assertEqual(sum(out[k] for k in ("clean_correct_corrupt_wrong",
                                              "clean_wrong_corrupt_correct",
                                              "both_correct", "both_wrong")), 5)

    def test_mask_is_the_pairing_unit(self):
        gt = np.array([[0, 0], [0, 0]])
        clean = np.zeros_like(gt)
        corrupt = np.ones_like(gt)
        mask = np.array([[True, False], [False, False]])
        out = paired_outcomes(gt, clean, corrupt, mask)
        self.assertEqual(out["valid_pixels"], 1)
        self.assertEqual(out["clean_correct_corrupt_wrong"], 1)
        self.assertEqual(out["prediction_changed"], 1)


if __name__ == "__main__":
    unittest.main()
