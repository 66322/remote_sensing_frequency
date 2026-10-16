"""Bounded CPU native DSM interface check; random weights, crop64, not accuracy."""
import copy
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
import torch
from model.rebuild_v1_optical_only import VisionTransformerOpticalOnly
from model.vitcross_seg_modeling_freqfusion import CONFIGS
from model.rebuild_v1_d26 import Expert
torch.set_num_threads(1);torch.manual_seed(42)
c=copy.deepcopy(CONFIGS['R50-ViT-B_16']);c.n_classes=6;c.n_skip=3;c.patches.grid=(4,4)
net=VisionTransformerOpticalOnly(c,img_size=64,num_classes=6).eval();x=torch.rand(1,64,64)
with torch.no_grad():
    expected=net(x[:,None].repeat(1,3,1,1));expert=Expert(net,net.segmentation_head[0],'dsm');actual,feature=expert(torch.rand(1,3,64,64),x)
torch.testing.assert_close(actual,expected,rtol=0,atol=0)
print('NATIVE_DSM_FORWARD_HOOK_PASS',tuple(actual.shape),tuple(feature.shape))
expert.configure(True);expert.train();loss=expert(torch.rand(1,3,64,64),x)[0].square().mean();loss.backward()
params=[p for p in expert.parameters() if p.requires_grad]
assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in params)
assert all(not m.training for m in expert.modules() if isinstance(m,torch.nn.modules.batchnorm._BatchNorm))
print('NATIVE_DSM_J0_GRADIENTS_PASS',sum(p.grad is not None for p in params),len(params),'BN_FROZEN=True')
