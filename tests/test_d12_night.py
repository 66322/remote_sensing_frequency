import sys
import types
import unittest
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from d12_semantic import decoder_maps, infer_at_pixels
from d12_night_probe import features, pooled_features, train_model, predict


class D12NightTests(unittest.TestCase):
    def test_pixel_extractor_preserves_alignment_across_overlapping_windows(self):
        fake = types.SimpleNamespace(positions=lambda length, patch, stride: [0, 2],
                                     DEVICE=torch.device("cpu"))
        previous = sys.modules.get("train_rebuild_v1_r02_budget_pilot")
        sys.modules["train_rebuild_v1_r02_budget_pilot"] = fake
        class Net(torch.nn.Module):
            def __init__(self):
                super().__init__()
                self.decoder = torch.nn.Identity()
            def forward(self, optical):
                hidden = self.decoder(optical)
                return torch.cat([hidden[:, :1]]*6, dim=1)
        try:
            optical = np.arange(36, dtype=np.float32).reshape(6, 6, 1)
            yy = np.array([0, 2, 3, 5])
            xx = np.array([0, 2, 3, 5])
            semantic, scores = infer_at_pixels(Net(), optical, None, yy, xx,
                                                patch=4, stride=2, batch=2,
                                                optical_only=True, return_scores=True)
            self.assertEqual(semantic.shape, (3, 4))
            self.assertEqual(scores.shape, (6, 4))
            np.testing.assert_allclose(scores[0], optical[yy, xx, 0])
        finally:
            if previous is None:
                sys.modules.pop("train_rebuild_v1_r02_budget_pilot", None)
            else:
                sys.modules["train_rebuild_v1_r02_budget_pilot"] = previous

    def test_decoder_measurements_have_pixel_grid_and_finite_values(self):
        hidden = torch.arange(2*4*8*8, dtype=torch.float32).reshape(2, 4, 8, 8)
        out = decoder_maps(hidden)
        self.assertEqual(tuple(out.shape), (2, 3, 8, 8))
        self.assertTrue(torch.isfinite(out).all())
        self.assertTrue(torch.allclose(out[:, 0], hidden.mean(1)))

    def test_semantic_frequency_shuffles_only_the_requested_block(self):
        n = 60
        rgb = np.zeros((6, n), np.float32)
        dual = np.zeros((6, n), np.float32)
        rgb[0] = 1
        dual[1] = 1
        sample = {"rgb_prob": rgb, "dual_prob": dual}
        for radius in (2, 8, 32):
            sample[f"rgb_energy_r{radius}"] = np.arange(n, dtype=np.float32)/n
            sample[f"dsm_energy_r{radius}"] = np.arange(n, dtype=np.float32)/n + radius
            sample[f"structure_r{radius}"] = np.arange(n, dtype=np.float32)/n
        semantic = dict(sem_rgb=np.tile(np.arange(n, dtype=np.float32), (3, 1)),
                        sem_dual=np.tile(np.arange(n, dtype=np.float32)+1, (3, 1)))
        base = features(sample, semantic, "ESF", 42, "6_7", "clean")
        shuffled_s = features(sample, semantic, "ESF_shuffleS", 42, "6_7", "clean")
        shuffled_f = features(sample, semantic, "ESF_shuffleF", 42, "6_7", "clean")
        self.assertEqual(base.shape, (n, 32))
        np.testing.assert_array_equal(base[:, :17], shuffled_s[:, :17])
        np.testing.assert_array_equal(base[:, :17], shuffled_f[:, :17])
        np.testing.assert_array_equal(base[:, 23:], shuffled_s[:, 23:])
        np.testing.assert_array_equal(base[:, 17:23], shuffled_f[:, 17:23])
        self.assertFalse(np.array_equal(base[:, 17:23], shuffled_s[:, 17:23]))
        self.assertFalse(np.array_equal(base[:, 23:], shuffled_f[:, 23:]))

    def test_pooled_shuffle_respects_tile_boundary(self):
        parts = []
        for tile, offset in (("3_11", 0), ("5_10", 100)):
            n = 20
            rgb = np.zeros((6, n), np.float32)
            dual = np.zeros((6, n), np.float32)
            rgb[0] = 1
            dual[1] = 1
            sample = {"rgb_prob": rgb, "dual_prob": dual}
            for radius in (2, 8, 32):
                sample[f"rgb_energy_r{radius}"] = np.arange(n, dtype=np.float32) + offset
                sample[f"dsm_energy_r{radius}"] = np.arange(n, dtype=np.float32) + offset + radius
                sample[f"structure_r{radius}"] = (np.arange(n, dtype=np.float32) + offset)/200
            semantic = dict(sem_rgb=np.tile(np.arange(n, dtype=np.float32)+offset, (3, 1)),
                            sem_dual=np.tile(np.arange(n, dtype=np.float32)+offset+1, (3, 1)))
            parts.append((tile, sample, semantic))
        for model, first in (("ESF_shuffleS", 17), ("ESF_shuffleF", 23)):
            actual = pooled_features(parts, model, 42, "clean")
            expected = np.concatenate([features(s, z, model, 42, tile, "clean")
                                       for tile, s, z in parts])
            np.testing.assert_array_equal(actual, expected)
            # The shifted block remains in its own tile's value range.
            self.assertLess(actual[:20, first].max(), actual[20:, first].min())

    def test_head_is_finite_and_capacity_control_is_larger(self):
        rng = np.random.default_rng(5)
        x = rng.normal(size=(180, 17)).astype(np.float32)
        y = np.repeat(np.arange(3), 60)
        cfg = dict(epochs=1, batch_size=64, learning_rate=.001, weight_decay=.0001)
        model = train_model(x, y, "Ecap", 42, cfg)
        p = predict(model, x)
        self.assertEqual(p.shape, (180, 3))
        self.assertTrue(np.isfinite(p).all())
        np.testing.assert_allclose(p.sum(1), 1, atol=1e-6)
        self.assertGreater(model["parameter_count"], (32+1)*64+64*3+3)


if __name__ == "__main__":
    unittest.main()
