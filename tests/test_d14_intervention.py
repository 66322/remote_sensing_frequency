import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from d14_intervention import intervene, changed_predictions


class D14InterventionTest(unittest.TestCase):
    def test_zero_keeps_availability_and_shift_breaks_alignment_without_changing_values(self):
        dsm = np.arange(30, dtype=np.float32).reshape(5, 6) / 30
        zero, missing = intervene(dsm, "zero_present")
        shifted, shift_missing = intervene(dsm, "shift_half")
        self.assertIsNone(missing)
        self.assertIsNone(shift_missing)
        self.assertTrue(np.all(zero == 0))
        self.assertFalse(np.array_equal(shifted, dsm))
        np.testing.assert_array_equal(np.sort(shifted.ravel()), np.sort(dsm.ravel()))

    def test_flip_count_excludes_ignored_pixels(self):
        gt = np.array([[0, 1, 255], [4, 5, 2]], np.uint8)
        clean = np.array([[0, 1, 0], [4, 0, 2]], np.uint8)
        altered = np.array([[1, 1, 1], [4, 5, 2]], np.uint8)
        row = changed_predictions(gt, clean, altered)
        self.assertEqual(row["flip_count"], 2)
        self.assertEqual(row["valid"], 5)
        self.assertEqual(row["flip_by_true_class"], [1, 0, 0, 0, 0, 1])


if __name__ == "__main__":
    unittest.main()
