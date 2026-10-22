import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import torch
from model.phase3_j_heads import FrozenExpertHead


class Heads(unittest.TestCase):
    def test_shapes_gradients_and_exact_missing_fallback(self):
        torch.manual_seed(5)
        r = torch.randn(2, 128, 8, 8)
        d = torch.randn_like(r)
        rl = torch.randn(2, 6, 8, 8)
        dl = torch.randn_like(rl)
        for arm in ("J1", "J2", "J3", "J4", "J5", "J6", "J7"):
            head = FrozenExpertHead(arm)
            second = r * 0.8 if arm == "J4" else None
            value = head(r, d, rl, dl, second_rgb=second)
            self.assertEqual(value.shape, rl.shape)
            value.mean().backward()
            self.assertTrue(any(p.grad is not None for p in head.parameters()))
            missing = torch.zeros((2, 1, 8, 8), dtype=torch.bool)
            no_dsm = head(r, d, rl, dl, dsm_available=missing, second_rgb=second)
            if arm in ("J3", "J4"):
                self.assertTrue(torch.equal(no_dsm, value))
            else:
                self.assertTrue(torch.equal(no_dsm, rl))

    def test_j5_and_j6_matched_parameters(self):
        torch.manual_seed(3)
        j5 = FrozenExpertHead("J5")
        torch.manual_seed(3)
        j6 = FrozenExpertHead("J6")
        self.assertEqual(list(j5.state_dict()), list(j6.state_dict()))
        for key in j5.state_dict():
            self.assertTrue(torch.equal(j5.state_dict()[key], j6.state_dict()[key]))


if __name__ == "__main__":
    unittest.main()
