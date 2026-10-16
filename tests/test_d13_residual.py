import sys
import unittest
import importlib.util
import json
import types
from pathlib import Path
from unittest import mock

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from d13_residual import (ARMS, INPUT_CHANNELS, ResidualHead, apply_residual,
                          features_for_arm, risk_loss, known_missing_mask)


class D13ResidualTest(unittest.TestCase):
    def test_all_arms_keep_same_parameter_count_and_identity_initialization(self):
        logits = torch.randn(1, 6, 8, 8)
        optical = torch.rand(1, 3, 8, 8)
        auxiliary = torch.rand(1, 1, 8, 8)
        decoder = torch.rand(1, 16, 8, 8)
        head = ResidualHead()
        count = sum(p.numel() for p in head.parameters())
        for arm in ARMS:
            x = features_for_arm(arm, logits, optical, auxiliary, decoder)
            self.assertEqual(x.shape[1], INPUT_CHANNELS)
            self.assertEqual(sum(p.numel() for p in head.parameters()), count)
            self.assertTrue(torch.equal(apply_residual(logits, head(x),
                                                      torch.ones(1, 8, 8, dtype=torch.bool)), logits))

    def test_missing_pixels_copy_anchor_even_with_nan_correction(self):
        anchor = torch.randn(1, 6, 4, 4)
        correction = torch.ones_like(anchor)
        correction[:, :, :2] = float("nan")
        available = torch.ones(1, 4, 4, dtype=torch.bool)
        available[:, :2] = False
        output = apply_residual(anchor, correction, available)
        self.assertTrue(torch.equal(output[:, :, :2], anchor[:, :, :2]))
        self.assertTrue(torch.equal(output[:, :, 2:], anchor[:, :, 2:] + 1))

    def test_risk_penalizes_damage_only_when_available(self):
        anchor = torch.tensor([[[[5.]], [[-5.]], [[-5.]], [[-5.]], [[-5.]], [[-5.]]]])
        harmful = -anchor
        target = torch.zeros((1, 1, 1), dtype=torch.long)
        available = torch.ones_like(target, dtype=torch.bool)
        ordinary, _, _ = risk_loss(harmful, anchor, target, available, False)
        protected, _, penalty = risk_loss(harmful, anchor, target, available, True)
        self.assertGreater(float(penalty), 0)
        self.assertGreater(float(protected), float(ordinary))
        _, _, absent_penalty = risk_loss(harmful, anchor, target, ~available, True)
        self.assertEqual(float(absent_penalty), 0)

    def test_degraded_region_never_becomes_missing(self):
        region = torch.ones((8, 8), dtype=torch.bool)
        self.assertIsNone(known_missing_mask("dsm_local_down8_q1", region))
        self.assertIsNone(known_missing_mask("dsm_blur5", region))
        self.assertIs(known_missing_mask("dsm_local_zero_q1", region), region)
        with self.assertRaises(ValueError):
            known_missing_mask("dsm_zero", None)

    def test_stage1_gate_requires_gain_harm_rescue_and_noise(self):
        root = Path(__file__).resolve().parents[1]
        config = root / "configs/rebuild_v1/d13_residual_overnight_20260924.json"
        cfg = json.loads(config.read_text(encoding="utf-8"))
        fake_r02 = types.ModuleType("train_rebuild_v1_r02_budget_pilot")
        fake_r02.read_json = lambda _path: cfg
        fake_train = types.ModuleType("train_rebuild_v1_d13_residual")
        fake_train.CONFIG = config
        fake_train.RUN_LABEL = "test"
        fake_train.sha256 = lambda _path: "test"
        script = root / "scripts/summarize_rebuild_v1_d13_residual.py"
        with mock.patch.dict(sys.modules, {fake_r02.__name__: fake_r02,
                                           fake_train.__name__: fake_train}):
            spec = importlib.util.spec_from_file_location("d13_summary_test", script)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

        def result(score, harm, rescue):
            data = {}
            for condition in cfg["evaluation"]["conditions"]:
                data[condition] = {"noboundary": {"metrics": {"mIoU_fg5": score},
                                                      "H": harm, "R": rescue,
                                                      "harm_count": 0 if condition == "dsm_zero" else 1},
                                   "tiles": {"tile": {"noboundary": {"H": harm}}}}
            return {"data": data, "baseline": {"noboundary":
                    {"metrics": {"mIoU_fg5": 0.80}}}}

        values = {(arm, 42): result(.85, .004, .01)
                  for arm in ("rgb_ce", "dsm_ce", "rgb_risk")}
        values[("dsm_risk", 42)] = result(.86, .003, .0095)
        passed = module.gate_for_seed(values, 42)
        self.assertTrue(passed["passed"], passed)
        values[("dsm_risk", 42)]["data"]["dsm_noise_std010"]["noboundary"]["metrics"]["mIoU_fg5"] = .79
        failed = module.gate_for_seed(values, 42)
        self.assertFalse(failed["passed"])
        self.assertFalse(failed["checks"]["noise_vs_R01"])


if __name__ == "__main__":
    unittest.main()
