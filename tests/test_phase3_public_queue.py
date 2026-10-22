import sys
import unittest
from pathlib import Path

import numpy as np
import torch

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "model")]

from phase3_public_runtime import _crop, _features, _instances_from_edges, _loss, _objects
from phase3_public_models import SmallUNet
from phase3_r_joint import JointHead


class PublicQueue(unittest.TestCase):
    def test_3dcd_features_and_gradients(self):
        shape = (136, 136)
        item = dict(id="a", group="g", rgb1=np.ones(shape+(3,), np.float32)*.5,
                    rgb2=np.ones(shape+(3,), np.float32)*.4,
                    dsm1=np.ones(shape, np.float32)*10,
                    dsm2=np.ones(shape, np.float32)*12,
                    valid=np.ones(shape, bool),
                    measurement_valid=np.ones(shape, bool),
                    changed=np.ones(shape, np.float32),
                    delta=np.ones(shape, np.float32)*2)
        before = _features("T", "robust_preprocess", item)
        item["valid"][0:10] = False
        self.assertTrue(np.array_equal(before, _features("T", "robust_preprocess", item)))
        for arm in ("plain", "nuisance_aug", "robust_preprocess", "hard_correspondence", "soft_no_match"):
            x, y, token = _crop(item, "T", arm, 7, 0)
            self.assertEqual(x.shape, (10,128,128))
            self.assertEqual(y.shape, (3,128,128))
            self.assertTrue(np.isfinite(x).all())
        net = SmallUNet(10,2)
        result = net(torch.from_numpy(x[None]))
        loss = _loss("T",arm,result,torch.from_numpy(y[None]))
        loss.backward()
        self.assertTrue(any(p.grad is not None for p in net.parameters()))

    def test_p3_relations_and_object_split(self):
        shape=(136,136)
        instance=np.zeros(shape,np.int32)
        instance[20:60,20:60]=1
        instance[60:100,60:100]=2
        item=dict(id="b",group="CH",rgb=np.ones(shape+(3,),np.float32)*.3,
                  height=np.ones(shape,np.float32)*5,height_valid=np.ones(shape,bool),
                  instance=instance)
        for arm in ("rgb_only","ordinary_fusion","rgb_relation","rgb_geometry_relation","shuffled_geometry"):
            x,y,_=_crop(item,"V",arm,11,0)
            self.assertEqual(x.shape,(5,128,128))
            self.assertEqual(y.shape,(5,128,128))
        net=SmallUNet(5,5)
        result=net(torch.from_numpy(x[None]))
        _loss("V",arm,result,torch.from_numpy(y[None])).backward()
        self.assertTrue(y[1].sum()>0)
        pred=_instances_from_edges(instance>0)
        counts=_objects(instance,pred)
        self.assertEqual(counts["tp"],2)

    def test_r_head_matches_aux_pair_initialization_shape(self):
        torch.manual_seed(123)
        plain=JointHead("conditional_joint")
        torch.manual_seed(123)
        aux=JointHead("conditional_joint_aux")
        self.assertTrue(all(torch.equal(a,b) for a,b in zip(plain.parameters(),aux.parameters())))
        r=torch.randn(2,128,8,8)
        d=torch.randn(2,128,8,8)
        rl=torch.randn(2,6,8,8)
        dl=torch.randn(2,6,8,8)
        self.assertEqual(plain(r,d,rl,dl).shape,(2,6,8,8))


if __name__=="__main__":unittest.main()
