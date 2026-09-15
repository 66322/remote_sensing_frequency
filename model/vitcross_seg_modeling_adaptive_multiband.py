"""
Modality-specific adaptive multi-band frequency routing.

Purpose
-------
Instead of assuming:
    Optical -> fixed high frequency
    DSM     -> fixed low frequency

the network dynamically selects frequency bands for each modality,
sample and spatial location.

Insertion:
    optical root / DSM root
        ->
    adaptive multi-band router
        ->
    original se_layer0

Only S0 is modified.
The original F0 decoder and subsequent backbone remain unchanged.

Identity initialization:
    router logits == 0
    softmax over K bands == 1/K
    band scale == K * 1/K == 1

therefore:
    calibrated_optical == optical
    calibrated_dsm == dsm

exactly at initialization.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

from model import vit_seg_modeling_resnet_skip as resnet_base
from model import vitcross_seg_modeling_freq_ablation as ablation_base


class ModalitySpecificAdaptiveMultiBandRouter(nn.Module):
    """
    S0 modality-specific adaptive frequency router.

    Four residual frequency bands are generated from nested
    local low-pass features:

        L1 = AvgPool3(F)
        L2 = AvgPool7(F)
        L3 = AvgPool15(F)
        L4 = AvgPool31(F)

        B1 = F  - L1
        B2 = L1 - L2
        B3 = L2 - L3
        B4 = L3 - L4

    L4 is kept untouched.

    Joint Optical/DSM frequency-energy cues predict separate
    K-band routing weights:

        Wo = softmax(Ro(cue))
        Wd = softmax(Rd(cue))

    Frequency gains:

        So = K * Wo
        Sd = K * Wd

    At zero-logit initialization:

        Wo = Wd = 1/K
        So = Sd = 1

    Hence the module is exactly identity at initialization.
    """

    def __init__(
        self,
        hidden_channels=16,
        kernel_sizes=(3, 7, 15, 31),
    ):
        super().__init__()

        self.kernel_sizes = tuple(
            int(k)
            for k in kernel_sizes
        )

        self.num_bands = len(
            self.kernel_sizes
        )

        if self.num_bands < 2:
            raise ValueError(
                "Need at least two frequency bands."
            )

        for k in self.kernel_sizes:
            if (
                k <= 0
                or k % 2 == 0
            ):
                raise ValueError(
                    f"Kernel must be positive odd: {k}"
                )

        # ----------------------------------------------------
        # Cue:
        #
        # Optical band-energy maps : K channels
        # DSM band-energy maps     : K channels
        # absolute discrepancy     : K channels
        #
        # Total = 3K.
        #
        # Output:
        # Optical logits : K
        # DSM logits     : K
        #
        # Total = 2K.
        # ----------------------------------------------------

        cue_channels = (
            3 * self.num_bands
        )

        out_channels = (
            2 * self.num_bands
        )

        self.context = nn.Sequential(
            nn.Conv2d(
                cue_channels,
                hidden_channels,
                kernel_size=3,
                padding=1,
                bias=True,
            ),
            nn.ReLU(inplace=True),
            nn.Conv2d(
                hidden_channels,
                out_channels,
                kernel_size=3,
                padding=1,
                bias=True,
            ),
        )

        # ----------------------------------------------------
        # Exact identity initialization.
        #
        # Zero logits -> uniform softmax -> K*(1/K)=1.
        # ----------------------------------------------------

        nn.init.zeros_(
            self.context[-1].weight
        )

        nn.init.zeros_(
            self.context[-1].bias
        )

        # Diagnostics only.
        self.last_weights = None
        self.last_optical_weights = None
        self.last_dsm_weights = None

        self.last_optical_scales = None
        self.last_dsm_scales = None

        self.last_optical_energy = None
        self.last_dsm_energy = None
        self.last_discrepancy = None

    @staticmethod
    def smooth(
        x,
        kernel_size,
    ):
        """
        Same-size deterministic local mean.

        count_include_pad=False avoids artificially depressing
        border averages.
        """

        pad = (
            kernel_size // 2
        )

        return F.avg_pool2d(
            x,
            kernel_size=kernel_size,
            stride=1,
            padding=pad,
            count_include_pad=False,
        )

    def decompose(
        self,
        x,
    ):
        """
        Returns:
            bands:
                B x K x C x H x W

            low_base:
                B x C x H x W
        """

        lows = []

        for k in self.kernel_sizes:
            lows.append(
                self.smooth(
                    x,
                    k,
                )
            )

        bands = []

        previous = x

        for low in lows:
            bands.append(
                previous - low
            )

            previous = low

        bands = torch.stack(
            bands,
            dim=1,
        )

        low_base = lows[-1]

        return (
            bands,
            low_base,
        )

    @staticmethod
    def band_energy(
        bands,
    ):
        """
        bands:
            B x K x C x H x W

        return:
            B x K x H x W
        """

        eps = 1e-6

        energy = torch.sqrt(
            bands.square().mean(
                dim=2,
            )
            + eps
        )

        return energy

    def forward(
        self,
        optical,
        dsm,
    ):
        if (
            optical.shape
            != dsm.shape
        ):
            raise RuntimeError(
                "Optical/DSM S0 feature shape mismatch: "
                f"{tuple(optical.shape)} vs "
                f"{tuple(dsm.shape)}"
            )

        # ----------------------------------------------------
        # 1. Multi-band decomposition
        # ----------------------------------------------------

        optical_bands, _ = (
            self.decompose(
                optical
            )
        )

        dsm_bands, _ = (
            self.decompose(
                dsm
            )
        )

        # ----------------------------------------------------
        # 2. Per-band spatial frequency energy
        # ----------------------------------------------------

        optical_energy_raw = (
            self.band_energy(
                optical_bands
            )
        )

        dsm_energy_raw = (
            self.band_energy(
                dsm_bands
            )
        )

        # ----------------------------------------------------
        # 3. Shared normalization
        #
        # Important:
        # Do NOT normalize Optical/DSM independently.
        #
        # Shared normalization preserves:
        #     - cross-modal energy relationship
        #     - cross-band energy relationship
        #
        # Router still receives spatially varying maps.
        # ----------------------------------------------------

        eps = 1e-6

        all_energy = torch.cat(
            [
                optical_energy_raw,
                dsm_energy_raw,
            ],
            dim=1,
        )

        shared_mean = all_energy.mean(
            dim=(1, 2, 3),
            keepdim=True,
        )

        optical_energy = (
            optical_energy_raw
            / (
                shared_mean
                + eps
            )
        )

        dsm_energy = (
            dsm_energy_raw
            / (
                shared_mean
                + eps
            )
        )

        discrepancy = torch.abs(
            optical_energy
            - dsm_energy
        )

        # ----------------------------------------------------
        # 4. Joint cross-modal routing cue
        # ----------------------------------------------------

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

        K = self.num_bands

        optical_logits = (
            logits[:, :K]
        )

        dsm_logits = (
            logits[:, K:]
        )

        # ----------------------------------------------------
        # 5. Independent modality-specific band routing
        # ----------------------------------------------------

        optical_weights = torch.softmax(
            optical_logits,
            dim=1,
        )

        dsm_weights = torch.softmax(
            dsm_logits,
            dim=1,
        )

        # Neutral routing:
        #
        # uniform 1/K
        # -> gain 1 for every band.
        optical_scales = (
            float(K)
            * optical_weights
        )

        dsm_scales = (
            float(K)
            * dsm_weights
        )

        # ----------------------------------------------------
        # 6. Adaptive residual reconstruction
        #
        # Original feature is preserved.
        #
        # Only deviations of each band gain from 1 modify it.
        # ----------------------------------------------------

        optical_delta = (
            (
                optical_scales
                - 1.0
            )
            .unsqueeze(2)
            * optical_bands
        ).sum(
            dim=1
        )

        dsm_delta = (
            (
                dsm_scales
                - 1.0
            )
            .unsqueeze(2)
            * dsm_bands
        ).sum(
            dim=1
        )

        calibrated_optical = (
            optical
            + optical_delta
        )

        calibrated_dsm = (
            dsm
            + dsm_delta
        )

        # ----------------------------------------------------
        # Diagnostics
        # ----------------------------------------------------

        self.last_optical_weights = (
            optical_weights.detach()
        )

        self.last_dsm_weights = (
            dsm_weights.detach()
        )

        self.last_weights = torch.stack(
            [
                optical_weights,
                dsm_weights,
            ],
            dim=1,
        ).detach()

        self.last_optical_scales = (
            optical_scales.detach()
        )

        self.last_dsm_scales = (
            dsm_scales.detach()
        )

        self.last_optical_energy = (
            optical_energy.detach()
        )

        self.last_dsm_energy = (
            dsm_energy.detach()
        )

        self.last_discrepancy = (
            discrepancy.detach()
        )

        return (
            calibrated_optical,
            calibrated_dsm,
        )


class FuseResNetV2AdaptiveMultiBand(
    resnet_base.FuseResNetV2
):
    """
    Original FuseResNetV2 with exactly one insertion:

        root/rootd
            ->
        adaptive multi-band router
            ->
        original se_layer0

    Everything after S0 remains unchanged.
    """

    def __init__(
        self,
        base_hybrid,
    ):
        # Reuse every module already initialized by the F0 model.
        # Do not instantiate another backbone.
        nn.Module.__init__(
            self
        )

        self.width = (
            base_hybrid.width
        )

        self.root = (
            base_hybrid.root
        )

        self.rootd = (
            base_hybrid.rootd
        )

        self.se_layer0 = (
            base_hybrid.se_layer0
        )

        self.se_layer1 = (
            base_hybrid.se_layer1
        )

        self.se_layer2 = (
            base_hybrid.se_layer2
        )

        self.se_layer3 = (
            base_hybrid.se_layer3
        )

        self.body = (
            base_hybrid.body
        )

        self.bodyd = (
            base_hybrid.bodyd
        )

        # The only newly initialized module.
        self.multiband0 = (
            ModalitySpecificAdaptiveMultiBandRouter(
                hidden_channels=16,
                kernel_sizes=(
                    3,
                    7,
                    15,
                    31,
                ),
            )
        )

    def forward(
        self,
        x,
        y,
    ):
        SE = True

        features = []

        b, c, in_size, _ = (
            x.size()
        )

        # Original modality-specific roots.
        x = self.root(x)
        y = self.rootd(y)

        # New pre-fusion adaptive multi-band routing.
        x, y = self.multiband0(
            x,
            y,
        )

        # Original first bimodal SE fusion.
        if SE:
            x = self.se_layer0(
                x,
                y,
            )

        features.append(
            x
        )

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

            features.append(
                feat
            )

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


class VisionTransformerAdaptiveMultiBand(
    ablation_base.VisionTransformerFreqAblation
):
    """
    F0 decoder + S0 modality-specific adaptive multi-band router.
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

        base_hybrid = (
            self
            .transformer
            .embeddings
            .hybrid_model
        )

        self.transformer.embeddings.hybrid_model = (
            FuseResNetV2AdaptiveMultiBand(
                base_hybrid=base_hybrid,
            )
        )

    def get_multiband_diagnostics(
        self,
    ):
        module = (
            self
            .transformer
            .embeddings
            .hybrid_model
            .multiband0
        )

        return {
            "weights":
                module.last_weights,

            "optical_weights":
                module.last_optical_weights,

            "dsm_weights":
                module.last_dsm_weights,

            "optical_scales":
                module.last_optical_scales,

            "dsm_scales":
                module.last_dsm_scales,

            "optical_energy":
                module.last_optical_energy,

            "dsm_energy":
                module.last_dsm_energy,

            "discrepancy":
                module.last_discrepancy,
        }

    load_from = (
        ablation_base
        .VisionTransformerFreqAblation
        .load_from
    )
