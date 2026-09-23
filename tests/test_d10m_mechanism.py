"""Numerical invariants; no dataset, checkpoint, GPU or output file required."""
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import numpy as np
from d10m_mechanism import translate, amplitude_error, sampled_structure, rescue_at_harm


class MechanismTests(unittest.TestCase):
    def test_translation_controls(self):
        x = np.random.default_rng(4).normal(size=(80, 96)).astype(np.float32)
        before = x.copy()
        for shift in (4, 16, 32):
            roll = translate(x, shift, True)
            edge = translate(x, shift, False)
            self.assertLess(amplitude_error(x, roll), 1e-6)
            np.testing.assert_array_equal(roll[:, shift:], edge[:, shift:])
            self.assertGreater(amplitude_error(x, edge), 1e-3)
        np.testing.assert_array_equal(before, x)

    def test_constant_scores_cannot_split_ties(self):
        rows = rescue_at_harm(np.ones(4), [1, 0, 0, 1], [0, 1, 1, 1], np.ones(4, bool), (0., .25))
        self.assertEqual(rows[0]["rescue"], 0.)
        self.assertEqual(rows[1]["harm"], .25)
        self.assertEqual(rows[1]["rescue"], .5)
        self.assertEqual(rows[1]["accuracy_gain"], .25)

    def test_missing_means_exact_zero_coverage(self):
        rows = rescue_at_harm([3., 2., 1.], [1, 0, 0], [0, 1, 1], np.zeros(3, bool))
        self.assertTrue(all(r["coverage"] == r["harm"] == r["rescue"] == 0 for r in rows))

    def test_envelope_matches_brute_force(self):
        rng = np.random.default_rng(2)
        for _ in range(20):
            score = rng.integers(-2, 3, 30)
            rc, dc, avail = rng.integers(0, 2, (3, 30)).astype(bool)
            rows = rescue_at_harm(score, rc, dc, avail, (0., .1, .2))
            for row in rows:
                rescues = [0.]
                for threshold in np.unique(score):
                    choose = avail & (score >= threshold)
                    h, r = np.mean(choose & rc & ~dc), np.mean(choose & ~rc & dc)
                    if h <= row["harm_budget"]:
                        rescues.append(r)
                self.assertAlmostEqual(row["rescue"], max(rescues))

    def test_structure_distinguishes_correspondence(self):
        rng = np.random.default_rng(1)
        x = rng.random((128, 128), dtype=np.float32)
        rgb = np.repeat(x[:, :, None], 3, axis=2)
        y, z = np.mgrid[40:88, 40:88]
        aligned = sampled_structure(rgb, x, y.ravel(), z.ravel())
        moved = sampled_structure(rgb, translate(x, 16, True), y.ravel(), z.ravel())
        self.assertGreater(aligned["structure_r8"].mean(), .99)
        self.assertLess(moved["structure_r8"].mean(), .2)
        flat = sampled_structure(np.zeros_like(rgb), np.zeros_like(x), y.ravel(), z.ravel())
        self.assertTrue(all(np.isfinite(v).all() for v in flat.values()))


if __name__ == "__main__":
    unittest.main()
