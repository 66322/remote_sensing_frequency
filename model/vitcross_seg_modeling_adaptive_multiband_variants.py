"""
Controlled ablations for adaptive multi-band routing.

R1: shared_spatial
    One spatial K-band routing map shared by Optical and DSM.

R2: modality_spatial
    Separate spatial K-band routing maps for Optical and DSM.
    This is the current main model and reuses the original R2 router.

R3: modality_global
    Separate content-adaptive K-band weights for Optical and DSM,
    but one set of weights per sample (no spatially varying routing).

R4: modality_static
    Separate learnable K-band weights for Optical and DSM,
    independent of the input content.

All variants:
    - use the same four bands: AvgPool kernels (3, 7, 15, 31)
    - operate at S0, before se_layer0
    - use scale = K * softmax(logits)
    - start as exact identity
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

from model import vit_seg_modeling_resnet_skip as resnet_base
from model import vitcross_seg_modeling_freq_ablation as ablation_base

from model.vitcross_seg_modeling_adaptive_multiband import (
    ModalitySpecificAdaptiveMultiBandRouter,
)


# ============================================================
# Common helpers
# ============================================================

def _normalize_energy(
    optical_energy_raw,
    dsm_energy_raw,
):
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
        / (shared_mean + eps)
    )

    dsm_energy = (
        dsm_energy_raw
        / (shared_mean + eps)
    )

    discrepancy = torch.abs(
        optical_energy
        - dsm_energy
    )

    return (
        optical_energy,
        dsm_energy,
        discrepancy,
    )


def _reconstruct(
    feature,
    bands,
    scales,
):
    """
    feature:
        B x C x H x W

    bands:
        B x K x C x H x W

    scales:
        B x K x H x W
        or
        B x K x 1 x 1
    """

    delta = (
        (
            scales - 1.0
        )
        .unsqueeze(2)
        * bands
    ).sum(
        dim=1
    )

    return (
        feature
        + delta
    )


def _save_diag(
    module,
    optical_weights,
    dsm_weights,
    optical_scales,
    dsm_scales,
    optical_energy,
    dsm_energy,
    discrepancy,
):
    module.last_optical_weights = (
        optical_weights.detach()
    )

    module.last_dsm_weights = (
        dsm_weights.detach()
    )

    module.last_weights = torch.stack(
        [
            optical_weights,
            dsm_weights,
        ],
        dim=1,
    ).detach()

    module.last_optical_scales = (
        optical_scales.detach()
    )

    module.last_dsm_scales = (
        dsm_scales.detach()
    )

    module.last_optical_energy = (
        optical_energy.detach()
    )

    module.last_dsm_energy = (
        dsm_energy.detach()
    )

    module.last_discrepancy = (
        discrepancy.detach()
    )


# ============================================================
# R1: Shared Spatial Router
# ============================================================

class SharedSpatialMultiBandRouter(
    ModalitySpecificAdaptiveMultiBandRouter
):
    """
    R1.

    One spatial K-band routing distribution is shared by both
    modalities.

    The cue is unchanged:
        [Optical energy, DSM energy, discrepancy]

    Difference from R2:
        R2 -> K Optical logits + K DSM logits
        R1 -> one K-logit map shared by both modalities
    """

    def __init__(
        self,
        hidden_channels=16,
        kernel_sizes=(3, 7, 15, 31),
    ):
        super().__init__(
            hidden_channels=hidden_channels,
            kernel_sizes=kernel_sizes,
        )

        K = self.num_bands

        # Preserve the first context Conv from the R2 design.
        #
        # Only replace the final output layer:
        #     2K -> K
        #
        # Exact identity:
        #     zero logits -> uniform 1/K -> scale 1.
        self.context[2] = nn.Conv2d(
            hidden_channels,
            K,
            kernel_size=3,
            padding=1,
            bias=True,
        )

        nn.init.zeros_(
            self.context[2].weight
        )

        nn.init.zeros_(
            self.context[2].bias
        )

    def forward(
        self,
        optical,
        dsm,
    ):
        if optical.shape != dsm.shape:
            raise RuntimeError(
                "Optical/DSM S0 feature shape mismatch: "
                f"{tuple(optical.shape)} vs "
                f"{tuple(dsm.shape)}"
            )

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

        (
            optical_energy,
            dsm_energy,
            discrepancy,
        ) = _normalize_energy(
            optical_energy_raw,
            dsm_energy_raw,
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

        K = self.num_bands

        shared_weights = torch.softmax(
            logits,
            dim=1,
        )

        shared_scales = (
            float(K)
            * shared_weights
        )

        calibrated_optical = (
            _reconstruct(
                optical,
                optical_bands,
                shared_scales,
            )
        )

        calibrated_dsm = (
            _reconstruct(
                dsm,
                dsm_bands,
                shared_scales,
            )
        )

        _save_diag(
            self,
            shared_weights,
            shared_weights,
            shared_scales,
            shared_scales,
            optical_energy,
            dsm_energy,
            discrepancy,
        )

        return (
            calibrated_optical,
            calibrated_dsm,
        )


# ============================================================
# R3: Modality-Specific Global Router
# ============================================================

class ModalitySpecificGlobalMultiBandRouter(
    ModalitySpecificAdaptiveMultiBandRouter
):
    """
    R3.

    Same cue network and parameter count as R2.

    R2:
        logits vary over H x W.

    R3:
        spatial logits are globally averaged before softmax,
        producing one Optical and one DSM band distribution
        for each image/sample.

    This isolates the value of spatially varying routing while
    retaining content-adaptive, modality-specific routing.
    """

    def forward(
        self,
        optical,
        dsm,
    ):
        if optical.shape != dsm.shape:
            raise RuntimeError(
                "Optical/DSM S0 feature shape mismatch: "
                f"{tuple(optical.shape)} vs "
                f"{tuple(dsm.shape)}"
            )

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

        (
            optical_energy,
            dsm_energy,
            discrepancy,
        ) = _normalize_energy(
            optical_energy_raw,
            dsm_energy_raw,
        )

        cue = torch.cat(
            [
                optical_energy,
                dsm_energy,
                discrepancy,
            ],
            dim=1,
        )

        spatial_logits = self.context(
            cue
        )

        # Key R3 ablation:
        # one routing vector per sample.
        logits = spatial_logits.mean(
            dim=(2, 3),
            keepdim=True,
        )

        K = self.num_bands

        optical_logits = (
            logits[:, :K]
        )

        dsm_logits = (
            logits[:, K:]
        )

        optical_weights = torch.softmax(
            optical_logits,
            dim=1,
        )

        dsm_weights = torch.softmax(
            dsm_logits,
            dim=1,
        )

        optical_scales = (
            float(K)
            * optical_weights
        )

        dsm_scales = (
            float(K)
            * dsm_weights
        )

        calibrated_optical = (
            _reconstruct(
                optical,
                optical_bands,
                optical_scales,
            )
        )

        calibrated_dsm = (
            _reconstruct(
                dsm,
                dsm_bands,
                dsm_scales,
            )
        )

        _save_diag(
            self,
            optical_weights,
            dsm_weights,
            optical_scales,
            dsm_scales,
            optical_energy,
            dsm_energy,
            discrepancy,
        )

        return (
            calibrated_optical,
            calibrated_dsm,
        )


# ============================================================
# R4: Modality-Specific Static Router
# ============================================================

class ModalitySpecificStaticMultiBandRouter(
    ModalitySpecificAdaptiveMultiBandRouter
):
    """
    R4.

    Two fixed learnable K-band distributions:
        one for Optical
        one for DSM

    They are shared across every sample and spatial location.

    This tests whether content-adaptive routing is actually
    necessary, rather than simply learning a dataset-level
    frequency preference.
    """

    def __init__(
        self,
        hidden_channels=16,
        kernel_sizes=(3, 7, 15, 31),
    ):
        # Reuse decomposition and diagnostic infrastructure.
        super().__init__(
            hidden_channels=hidden_channels,
            kernel_sizes=kernel_sizes,
        )

        # Remove the content router entirely.
        self.context = nn.Identity()

        K = self.num_bands

        self.static_logits = nn.Parameter(
            torch.zeros(
                2,
                K,
            )
        )

    def forward(
        self,
        optical,
        dsm,
    ):
        if optical.shape != dsm.shape:
            raise RuntimeError(
                "Optical/DSM S0 feature shape mismatch: "
                f"{tuple(optical.shape)} vs "
                f"{tuple(dsm.shape)}"
            )

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

        # Energies are retained only for diagnostics.
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

        (
            optical_energy,
            dsm_energy,
            discrepancy,
        ) = _normalize_energy(
            optical_energy_raw,
            dsm_energy_raw,
        )

        K = self.num_bands

        weights = torch.softmax(
            self.static_logits,
            dim=1,
        )

        optical_weights = (
            weights[0]
            .view(1, K, 1, 1)
            .expand(
                optical.shape[0],
                -1,
                -1,
                -1,
            )
        )

        dsm_weights = (
            weights[1]
            .view(1, K, 1, 1)
            .expand(
                dsm.shape[0],
                -1,
                -1,
                -1,
            )
        )

        optical_scales = (
            float(K)
            * optical_weights
        )

        dsm_scales = (
            float(K)
            * dsm_weights
        )

        calibrated_optical = (
            _reconstruct(
                optical,
                optical_bands,
                optical_scales,
            )
        )

        calibrated_dsm = (
            _reconstruct(
                dsm,
                dsm_bands,
                dsm_scales,
            )
        )

        _save_diag(
            self,
            optical_weights,
            dsm_weights,
            optical_scales,
            dsm_scales,
            optical_energy,
            dsm_energy,
            discrepancy,
        )

        return (
            calibrated_optical,
            calibrated_dsm,
        )


# ============================================================
# Router factory
# ============================================================

ROUTER_MODES = (
    "shared_spatial",
    "modality_spatial",
    "modality_global",
    "modality_static",
)


def build_multiband_router(
    router_mode,
):
    kwargs = dict(
        hidden_channels=16,
        kernel_sizes=(
            3,
            7,
            15,
            31,
        ),
    )

    if router_mode == "shared_spatial":
        return SharedSpatialMultiBandRouter(
            **kwargs
        )

    if router_mode == "modality_spatial":
        return ModalitySpecificAdaptiveMultiBandRouter(
            **kwargs
        )

    if router_mode == "modality_global":
        return ModalitySpecificGlobalMultiBandRouter(
            **kwargs
        )

    if router_mode == "modality_static":
        return ModalitySpecificStaticMultiBandRouter(
            **kwargs
        )

    raise ValueError(
        f"Unknown router_mode: {router_mode}"
    )


# ============================================================
# Hybrid backbone wrapper
# ============================================================

class FuseResNetV2MultiBandVariant(
    resnet_base.FuseResNetV2
):
    """
    Original F0 hybrid backbone with exactly one S0 insertion.
    """

    def __init__(
        self,
        base_hybrid,
        router_mode,
    ):
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

        self.router_mode = (
            str(router_mode)
        )

        self.multiband0 = (
            build_multiband_router(
                self.router_mode
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

        x = self.root(x)
        y = self.rootd(y)

        x, y = self.multiband0(
            x,
            y,
        )

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

            if x.size()[2] != right_size:
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


# ============================================================
# Full segmentation model
# ============================================================

class VisionTransformerMultiBandVariant(
    ablation_base.VisionTransformerFreqAblation
):
    def __init__(
        self,
        config,
        img_size=224,
        num_classes=6,
        zero_head=False,
        vis=False,
        router_mode="modality_spatial",
    ):
        if router_mode not in ROUTER_MODES:
            raise ValueError(
                f"Unknown router_mode: {router_mode}"
            )

        self.router_mode = (
            router_mode
        )

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
            FuseResNetV2MultiBandVariant(
                base_hybrid=base_hybrid,
                router_mode=router_mode,
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
