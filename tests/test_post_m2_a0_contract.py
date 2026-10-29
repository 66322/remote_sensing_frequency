import importlib.util
import unittest
import warnings
from pathlib import Path

import numpy as np

SOURCE=Path(__file__).resolve().parents[1]/"scripts/post_m2_a0.py"
spec=importlib.util.spec_from_file_location("post_m2_a0",SOURCE)
a0=importlib.util.module_from_spec(spec)
spec.loader.exec_module(a0)


class ContractTests(unittest.TestCase):
    def test_frozen_features_can_train_readout(self):
        import torch

        class TinyEncoder:
            def forward_features(self, images):
                patches=torch.nn.functional.avg_pool2d(images,14,14)
                return {"x_norm_patchtokens":patches.flatten(2).transpose(1,2)}

        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", message="User provided device_type of 'cuda'")
            features=a0.extract(TinyEncoder(),torch.rand(1,3,28,28),14)
        self.assertFalse(features.is_inference())
        head=torch.nn.Conv2d(3,6,1)
        head(features).square().mean().backward()
        self.assertIsNotNone(head.weight.grad)
        self.assertTrue(bool(torch.isfinite(head.weight.grad).all()))

    def test_fg5_is_first_five_classes_not_clutter(self):
        cm=np.diag([10,20,30,40,50,0])
        observed=a0.metrics(cm)
        self.assertEqual(observed["nb_fg5_miou"],100.0)
        self.assertEqual(observed["valid_pixels"],150)

    def test_full_tile_sliding_windows_cover_central_region(self):
        positions=a0.coords(6000,6000)
        axis=sorted({y for y,_ in positions})
        self.assertEqual(axis[0],0)
        self.assertEqual(axis[-1],5488)
        self.assertLessEqual(max(y-x for x,y in zip(axis,axis[1:])),256)

    def test_border_exclusion_and_ignore_label(self):
        gt=np.full((2048,2048),255,np.uint8)
        pred=np.zeros_like(gt)
        gt[512:1536,512:1536]=0
        cm=a0.cm_tile(pred,gt)
        self.assertEqual(int(cm[0,0]),1024**2)
        self.assertEqual(int(cm.sum()),1024**2)


if __name__=="__main__":
    unittest.main()
