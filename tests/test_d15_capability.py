import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import d15_capability as capability


class D15CapabilityTest(unittest.TestCase):
    def test_dsm_representation_and_rgb_pairing(self):
        dsm = np.arange(64, dtype=np.float32).reshape(8, 8) / 63
        rgb = np.stack([dsm, 1 - dsm, dsm / 2], axis=-1)
        x = capability.as_three_channels(dsm)
        self.assertEqual(x.shape, (8, 8, 3))
        self.assertTrue(np.array_equal(x[:, :, 0], x[:, :, 2]))
        down_rgb, unchanged_dsm = capability.condition_data(rgb, dsm, "rgb_down4")
        self.assertTrue(np.array_equal(unchanged_dsm, dsm))
        self.assertFalse(np.array_equal(down_rgb, rgb))
        self.assertTrue(np.array_equal(capability.second_stream("C-OO-QD", down_rgb, unchanged_dsm),
                                       down_rgb.mean(axis=2).astype(np.float32)))
        self.assertFalse(np.array_equal(capability.second_stream("C-OO-QD", down_rgb, unchanged_dsm),
                                        rgb.mean(axis=2).astype(np.float32)))
        _, absent_dsm = capability.condition_data(rgb, dsm, "rgb_down4_dsm_zero")
        self.assertTrue(np.array_equal(absent_dsm, np.zeros_like(dsm)))
        local, _ = capability.condition_data(rgb, dsm, "rgb_local_down4_q1")
        self.assertTrue(np.array_equal(local[0, 0], rgb[0, 0]))
        self.assertFalse(np.array_equal(local[3, 3], rgb[3, 3]))

    def test_joint_counts_use_valid_pixels_only(self):
        gt = np.array([[0, 1, 255], [2, 1, 0]], dtype=np.uint8)
        baseline = np.array([[0, 0, 0], [2, 0, 1]], dtype=np.uint8)
        candidate = np.array([[0, 1, 1], [0, 0, 1]], dtype=np.uint8)
        counts = capability.joint(gt, baseline, candidate)
        self.assertEqual(counts["valid"], 5)
        self.assertEqual(counts["both_correct"], 1)
        self.assertEqual(counts["only_r01_correct"], 1)
        self.assertEqual(counts["only_candidate_correct"], 1)
        self.assertEqual(counts["both_wrong"], 2)


if __name__ == "__main__":
    unittest.main()
