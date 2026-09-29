import unittest
import torch
from torch import nn
from torch.nn import functional as F

from model.rebuild_v1_day_portfolio import AContinuation, BAnchoredResidual, CDRestorationSegmenter, highpass


class TinyEncoder(nn.Module):
    def __init__(self):
        super().__init__()
        self.proj = nn.Conv2d(3, 384, 1)
        self.blocks = nn.ModuleList(nn.Conv2d(384, 384, 1, groups=384) for _ in range(5))

    def forward_features(self, x):
        x = F.avg_pool2d(self.proj(x), 14, 14)
        for block in self.blocks:
            x = block(x)
        return {'x_norm_patchtokens': x.flatten(2).transpose(1, 2)}


class PortfolioTests(unittest.TestCase):
    def test_a_last4_receives_gradient(self):
        torch.manual_seed(42)
        model = AContinuation(TinyEncoder(), 'M0', True)
        x = torch.rand(1, 3, 28, 28)
        y = torch.rand(1, 28, 28)
        model(x, y).mean().backward()
        self.assertFalse(model.encoder.blocks[0].weight.requires_grad)
        self.assertIsNotNone(model.encoder.blocks[-1].weight.grad)
        self.assertTrue(torch.isfinite(model.encoder.blocks[-1].weight.grad).all())

    def test_b_zero_aux_equals_anchor(self):
        torch.manual_seed(42)
        model = BAnchoredResidual(TinyEncoder(), 'B3').eval()
        x = torch.rand(1, 3, 28, 28)
        zero = torch.zeros(1, 28, 28)
        with torch.no_grad():
            actual = model(x, zero)
            feature = F.interpolate(model.rgb(__import__('model.rebuild_v1_day_portfolio', fromlist=['encoded_features']).encoded_features(model, x)), size=(7, 7), mode='nearest')
            anchor = F.interpolate(model.decoder(feature), size=(28, 28), mode='nearest')
        self.assertTrue(torch.equal(actual, anchor))

    def test_c_ce_reaches_restoration_front(self):
        torch.manual_seed(42)
        model = CDRestorationSegmenter(TinyEncoder(), 'C1', 2)
        x = torch.rand(1, 3, 28, 28)
        logits, restored = model.forward_with_restored(x, torch.zeros(1, 28, 28))
        F.cross_entropy(logits, torch.zeros(1, 28, 28, dtype=torch.long)).backward()
        self.assertEqual(restored.shape, x.shape)
        self.assertGreater(model.front.net[-1].weight.grad.abs().sum().item(), 0)
        self.assertFalse(model.encoder.proj.weight.requires_grad)
        self.assertTrue(torch.isfinite(highpass(restored)).all())

    def test_capacity_matching_and_d_branch(self):
        torch.manual_seed(42)
        counts=[]
        for arm in ('B1','B2','B3','B4'):
            model=BAnchoredResidual(TinyEncoder(),arm)
            counts.append(sum(p.numel() for p in model.parameters() if p.requires_grad))
        self.assertEqual(len(set(counts)),1)
        model=CDRestorationSegmenter(TinyEncoder(),'D_ph_dsm',4)
        logits,restored=model.forward_with_restored(torch.rand(1,3,28,28),torch.rand(1,28,28))
        self.assertEqual(tuple(logits.shape),(1,6,28,28))
        self.assertEqual(tuple(restored.shape),(1,3,28,28))


if __name__ == '__main__':
    unittest.main()
