"""Trainable RGB/DSM representation comparisons with an identical output contract."""
import torch
from torch import nn
from phase3_j_heads import FrozenExpertHead


class JointHead(nn.Module):
    def __init__(self, arm):
        super().__init__()
        if arm not in ("concat_joint", "conditional_joint", "conditional_joint_aux"):
            raise ValueError(arm)
        self.arm = arm
        self.head = FrozenExpertHead("J2" if arm == "concat_joint" else "J6")

    def forward(self, r_feature, d_feature, r_logits, d_logits, second_rgb=None):
        # The DSM semantic branch participates in the primary loss in every arm.
        # Thus the auxiliary DSM loss is the only difference in the aux pair.
        return self.head(r_feature, d_feature, r_logits, d_logits) + .1 * d_logits


def forward_joint(rgb_expert, dsm_expert, head, rgb, dsm):
    rf = rgb_expert.encode(rgb)
    df = dsm_expert.encode(dsm[:, None].repeat(1, 3, 1, 1))
    rl = rgb_expert.decoder(rf)
    dl = dsm_expert.decoder(df)
    return head(rf, df, rl, dl), dl
