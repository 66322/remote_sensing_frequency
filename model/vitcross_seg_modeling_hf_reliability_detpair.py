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


class CrossModalHFReliabilityCalibration(nn.Module):
    """
    P2-H: pre-fusion cross-modal HF reliability calibration.

    Given modality-specific S0 features:

        Fo = Lo + Ho
        Fd = Ld + Hd

    predict complementary spatial reliability:

        [wo, wd] = softmax(g(Eo, Ed, |Eo-Ed|))

    and define:

        So = 2 * wo
        Sd = 2 * wd

    so that:

        Fo' = Fo + (So - 1) * Ho
        Fd' = Fd + (Sd - 1) * Hd

    Initialization:
        logits == 0
        wo == wd == 0.5
        So == Sd == 1

    Therefore P2-H is exactly F0 at initialization.

    Only S0 high-frequency components are calibrated.
    Low-frequency components and the original SE fusion remain
    structurally unchanged.
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
                2,
                kernel_size=3,
                padding=1,
                bias=True,
            ),
        )

        # Neutral reliability initialization:
        # logits=(0,0) -> softmax=(0.5,0.5)
        # -> both HF scales exactly 1.
        nn.init.zeros_(
            self.context[-1].weight
        )
        nn.init.zeros_(
            self.context[-1].bias
        )

        # Diagnostics.
        self.last_weights = None
        self.last_optical_scale = None
        self.last_dsm_scale = None

        # Compatibility diagnostic:
        # last_scale refers to DSM scale, allowing the existing
        # P1-style logger to be reused temporarily if required.
        self.last_scale = None

        self.last_discrepancy = None

    @staticmethod
    def deterministic_reflect_pad1(x):
        """
        Deterministic forward-equivalent reflect padding for pad=1.

        Avoids CUDA ReflectionPad2d backward nondeterminism.
        """
        if x.ndim != 4:
            raise RuntimeError(
                f"Expected BCHW tensor, got "
                f"shape={tuple(x.shape)}"
            )

        if (
            x.shape[-2] < 2
            or x.shape[-1] < 2
        ):
            raise RuntimeError(
                "Reflect pad=1 requires H,W >= 2"
            )

        x = torch.cat(
            [
                x[:, :, 1:2, :],
                x,
                x[:, :, -2:-1, :],
            ],
            dim=2,
        )

        x = torch.cat(
            [
                x[:, :, :, 1:2],
                x,
                x[:, :, :, -2:-1],
            ],
            dim=3,
        )

        return x

    @staticmethod
    def local_decompose(x):
        padded = (
            CrossModalHFReliabilityCalibration
            .deterministic_reflect_pad1(
                x
            )
        )

        low = F.avg_pool2d(
            padded,
            kernel_size=3,
            stride=1,
            padding=0,
        )

        high = x - low

        return low, high

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

        # Normalize each patch/modality separately.
        # The cue represents WHERE HF occurs rather than
        # raw cross-modal feature amplitude.
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

        _, dsm_high = (
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

        logits = self.context(
            cue
        )

        weights = torch.softmax(
            logits,
            dim=1,
        )

        optical_weight = (
            weights[:, 0:1]
        )

        dsm_weight = (
            weights[:, 1:2]
        )

        # Complementary HF scales:
        #
        # optical_scale + dsm_scale == 2
        #
        # neutral:
        #     0.5 / 0.5 -> 1 / 1
        optical_scale = (
            2.0 * optical_weight
        )

        dsm_scale = (
            2.0 * dsm_weight
        )

        calibrated_optical = (
            optical
            + (
                optical_scale - 1.0
            )
            * optical_high
        )

        calibrated_dsm = (
            dsm
            + (
                dsm_scale - 1.0
            )
            * dsm_high
        )

        self.last_weights = (
            weights.detach()
        )

        self.last_optical_scale = (
            optical_scale.detach()
        )

        self.last_dsm_scale = (
            dsm_scale.detach()
        )

        self.last_scale = (
            dsm_scale.detach()
        )

        self.last_discrepancy = (
            discrepancy.detach()
        )

        return (
            calibrated_optical,
            calibrated_dsm,
        )


class FuseResNetV2HFReliability(
    resnet_base.FuseResNetV2
):
    """
    Original FuseResNetV2 with exactly one insertion:

        root/rootd
            ->
        cross-modal HF reliability calibration
            ->
        original se_layer0

    Everything after S0 follows the original implementation.
    """

    def __init__(
        self,
        base_hybrid,
    ):
        # Do NOT instantiate another FuseResNetV2 here.
        #
        # Reuse every module already created by the F0
        # constructor so that all common parameters keep
        # exactly the same seed-42 initialization.
        nn.Module.__init__(self)

        self.width = base_hybrid.width

        self.root = base_hybrid.root
        self.rootd = base_hybrid.rootd

        self.se_layer0 = base_hybrid.se_layer0
        self.se_layer1 = base_hybrid.se_layer1
        self.se_layer2 = base_hybrid.se_layer2
        self.se_layer3 = base_hybrid.se_layer3

        self.body = base_hybrid.body
        self.bodyd = base_hybrid.bodyd

        # The only newly initialized module.
        self.hfrely0 = (
            CrossModalHFReliabilityCalibration(
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
        # P2-H: cross-modal HF reliability calibration.
        #
        # Both modality-specific features remain separate.
        # Only their HF residuals are adaptively calibrated.
        # ----------------------------------------------------
        x, y = self.hfrely0(
            x,
            y,
        )

        # Original first bimodal SE fusion is unchanged.
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


class VisionTransformerHFReliability(
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

        # Reuse the already-created F0 hybrid backbone.
        # This avoids reinitializing DynamicConv/root/body.
        base_hybrid = (
            self.transformer
            .embeddings
            .hybrid_model
        )

        self.transformer.embeddings.hybrid_model = (
            FuseResNetV2HFReliability(
                base_hybrid=base_hybrid,
            )
        )

    def get_hfrely_diagnostics(
        self,
    ):
        module = (
            self
            .transformer
            .embeddings
            .hybrid_model
            .hfrely0
        )

        return {
            # Backward-compatible P1-style aliases.
            "scale": module.last_scale,
            "discrepancy": (
                module.last_discrepancy
            ),

            # P2-H explicit diagnostics.
            "weights": (
                module.last_weights
            ),
            "optical_scale": (
                module.last_optical_scale
            ),
            "dsm_scale": (
                module.last_dsm_scale
            ),
        }

    # Preserve original pretrained loader.
    load_from = (
        ablation_base
        .VisionTransformerFreqAblation
        .load_from
    )
