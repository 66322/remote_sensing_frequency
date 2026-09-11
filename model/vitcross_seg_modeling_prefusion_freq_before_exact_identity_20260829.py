"""
Pre-fusion cross-modal frequency calibration.

P1 hypothesis:
    Calibrate DSM high-frequency information before the first
    Optical-DSM SE fusion using cross-modal HF-energy reliability.

Important:
    - Only S0 is modified.
    - Optical branch is unchanged.
    - Decoder is F0 (no FreqFusion).
    - Initialization is identity:
          calibrated_dsm == original_dsm
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

from model import vit_seg_modeling_resnet_skip as resnet_base
from model import vitcross_seg_modeling_freq_ablation as ablation_base


class CrossModalHFCalibration(nn.Module):
    """
    Cross-modal HF-energy guided DSM calibration.

    scale = 1 + tanh(q), range (0, 2)

    q == 0:
        scale == 1
        output == original DSM feature
    """

    def __init__(
        self,
        hidden_channels=16,
    ):
        super().__init__()

        self.context = nn.Sequential(
            nn.Conv2d(
                3,
                hidden_channels,
                kernel_size=3,
                padding=1,
                bias=True,
            ),
            nn.ReLU(inplace=True),
            nn.Conv2d(
                hidden_channels,
                1,
                kernel_size=3,
                padding=1,
                bias=True,
            ),
        )

        # Exact identity initialization.
        nn.init.zeros_(
            self.context[-1].weight
        )
        nn.init.zeros_(
            self.context[-1].bias
        )

        self.last_scale = None
        self.last_discrepancy = None

    @staticmethod
    def local_decompose(x):
        smooth = F.avg_pool2d(
            F.pad(
                x,
                (1, 1, 1, 1),
                mode="reflect",
            ),
            kernel_size=3,
            stride=1,
            padding=0,
        )

        high = x - smooth

        return smooth, high

    @staticmethod
    def hf_energy(high):
        eps = 1e-6

        energy = torch.sqrt(
            high.square().mean(
                dim=1,
                keepdim=True,
            )
            + eps
        )

        energy = (
            energy
            / (
                energy.mean(
                    dim=(-2, -1),
                    keepdim=True,
                )
                + eps
            )
        )

        return energy

    def forward(
        self,
        optical,
        dsm,
    ):
        _, optical_high = (
            self.local_decompose(
                optical
            )
        )

        dsm_low, dsm_high = (
            self.local_decompose(
                dsm
            )
        )

        optical_energy = (
            self.hf_energy(
                optical_high
            )
        )

        dsm_energy = (
            self.hf_energy(
                dsm_high
            )
        )

        discrepancy = torch.abs(
            optical_energy
            - dsm_energy
        )

        cue = torch.cat(
            [
                optical_energy,
                dsm_energy,
                discrepancy,
            ],
            dim=1,
        )

        q = self.context(cue)

        scale = (
            1.0
            + torch.tanh(q)
        )

        calibrated_dsm = (
            dsm_low
            + scale * dsm_high
        )

        # Diagnostics only.
        self.last_scale = (
            scale.detach()
        )

        self.last_discrepancy = (
            discrepancy.detach()
        )

        return calibrated_dsm


class FuseResNetV2PreFusionFreq(
    resnet_base.FuseResNetV2
):
    """
    Original FuseResNetV2 with exactly one insertion:

        root/rootd
            ->
        pre-frequency calibration on DSM
            ->
        original se_layer0

    Everything after S0 follows the original implementation.
    """

    def __init__(
        self,
        block_units,
        width_factor,
    ):
        super().__init__(
            block_units=block_units,
            width_factor=width_factor,
        )

        self.prefreq0 = (
            CrossModalHFCalibration(
                hidden_channels=16,
            )
        )

    def forward(
        self,
        x,
        y,
    ):
        SE = True

        features = []

        b, c, in_size, _ = x.size()

        # Original modality-specific roots.
        x = self.root(x)
        y = self.rootd(y)

        # ----------------------------------------------------
        # P1: only new operation.
        # ----------------------------------------------------
        y = self.prefreq0(
            x,
            y,
        )

        # Original first bimodal fusion.
        if SE:
            x = self.se_layer0(
                x,
                y,
            )

        features.append(x)

        x = nn.MaxPool2d(
            kernel_size=3,
            stride=2,
            padding=0,
        )(x)

        y = nn.MaxPool2d(
            kernel_size=3,
            stride=2,
            padding=0,
        )(y)

        for i in range(
            len(self.body) - 1
        ):
            x = self.body[i](x)
            y = self.bodyd[i](y)

            if SE:
                if i == 0:
                    x = self.se_layer1(
                        x,
                        y,
                    )

                if i == 1:
                    x = self.se_layer2(
                        x,
                        y,
                    )

            right_size = int(
                in_size
                / 4
                / (i + 1)
            )

            if (
                x.size()[2]
                != right_size
            ):
                pad = (
                    right_size
                    - x.size()[2]
                )

                assert (
                    pad < 3
                    and pad > 0
                ), (
                    "x {} should {}"
                    .format(
                        x.size(),
                        right_size,
                    )
                )

                feat = torch.zeros(
                    (
                        b,
                        x.size()[1],
                        right_size,
                        right_size,
                    ),
                    device=x.device,
                    dtype=x.dtype,
                )

                feat[
                    :,
                    :,
                    0:x.size()[2],
                    0:x.size()[3],
                ] = x[:]

            else:
                feat = x

            features.append(feat)

        x = self.body[-1](x)
        y = self.bodyd[-1](y)

        if SE:
            x = self.se_layer3(
                x,
                y,
            )

        return (
            x,
            y,
            features[::-1],
        )


class VisionTransformerPreFusionFreq(
    ablation_base.VisionTransformerFreqAblation
):
    """
    F0 decoder + S0 pre-fusion frequency calibration.
    """

    def __init__(
        self,
        config,
        img_size=224,
        num_classes=6,
        zero_head=False,
        vis=False,
    ):
        super().__init__(
            config=config,
            img_size=img_size,
            num_classes=num_classes,
            zero_head=zero_head,
            vis=vis,
            freq_variant="F0",
        )

        self.transformer.embeddings.hybrid_model = (
            FuseResNetV2PreFusionFreq(
                block_units=(
                    config.resnet.num_layers
                ),
                width_factor=(
                    config.resnet.width_factor
                ),
            )
        )

    def get_prefreq_diagnostics(
        self,
    ):
        module = (
            self
            .transformer
            .embeddings
            .hybrid_model
            .prefreq0
        )

        return {
            "scale": module.last_scale,
            "discrepancy": (
                module.last_discrepancy
            ),
        }

    # Preserve original pretrained loader.
    load_from = (
        ablation_base
        .VisionTransformerFreqAblation
        .load_from
    )
