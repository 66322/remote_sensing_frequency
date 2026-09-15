"""
E51-B: Modality-specific physical frequency calibration.

Optical:
    unchanged fixed pixel-frequency decomposition.

DSM:
    per-sample physical-coordinate decomposition.

For a training sample with effective augmentation scale s:

    effective input GSD = native_GSD / s

To map DSM S0 features back to the canonical native-GSD
coordinate system, resize by:

    canonical_factor = 1 / s

Then apply exactly the same fixed kernels:

    (3, 7, 15, 31)

Finally resize each band back to the original S0 feature size.

At s = 1:
    the DSM decomposition is exactly identical to the original R4.

The R4 static router remains unchanged:
    separate Optical / DSM learnable static K-band weights.
"""

import torch
import torch.nn.functional as F

from model.vitcross_seg_modeling_adaptive_multiband_variants import (
    ModalitySpecificStaticMultiBandRouter,
    VisionTransformerMultiBandVariant,
    _normalize_energy,
    _reconstruct,
    _save_diag,
)


class PhysicalDSMStaticMultiBandRouter(
    ModalitySpecificStaticMultiBandRouter
):
    """
    R4 static router with:

        Optical -> ordinary pixel-coordinate bands
        DSM     -> physical-coordinate bands

    Sample scales are one-shot state:
        set_sample_scales(...)
        -> one forward consumes them
        -> state automatically resets to None.

    If no scales are supplied, all samples use s=1.
    This is exactly the native-GSD inference behavior.
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

        self._pending_sample_scales = None

        # Diagnostics only.
        self.last_sample_scales = None
        self.last_canonical_sizes = None

    def set_sample_scales(
        self,
        scales,
    ):
        if scales is None:
            self._pending_sample_scales = None
            return

        values = [
            float(x)
            for x in scales
        ]

        for x in values:
            if (
                not (x > 0.0)
                or not torch.isfinite(
                    torch.tensor(x)
                )
            ):
                raise ValueError(
                    f"Invalid sample scale: {x}"
                )

        self._pending_sample_scales = tuple(
            values
        )

    def _take_sample_scales(
        self,
        batch_size,
    ):
        pending = (
            self._pending_sample_scales
        )

        # One-shot consumption prevents stale training scales
        # leaking into evaluation.
        self._pending_sample_scales = None

        if pending is None:
            scales = [
                1.0
                for _ in range(batch_size)
            ]
        else:
            if len(pending) != batch_size:
                raise RuntimeError(
                    "sample scale count mismatch: "
                    f"got {len(pending)}, "
                    f"batch={batch_size}"
                )

            scales = list(
                pending
            )

        self.last_sample_scales = (
            tuple(scales)
        )

        return scales

    def physical_dsm_decompose(
        self,
        dsm,
        sample_scales,
    ):
        """
        DSM physical-coordinate decomposition.

        dsm:
            B x C x H x W

        sample_scales:
            one effective augmentation scale per sample.

        Returns:
            B x K x C x H x W
        """

        B, C, H, W = dsm.shape
        K = self.num_bands

        if len(sample_scales) != B:
            raise RuntimeError(
                "physical DSM scale count mismatch: "
                f"{len(sample_scales)} vs B={B}"
            )

        output_bands = []
        canonical_sizes = []

        max_kernel = max(
            self.kernel_sizes
        )

        for b in range(B):
            s = float(
                sample_scales[b]
            )

            if s <= 0.0:
                raise RuntimeError(
                    f"Invalid physical scale {s}"
                )

            # Native reference coordinate:
            #
            #     factor = 1 / s
            #
            # s < 1:
            #     coarser effective GSD -> upsample to canonical grid.
            #
            # s > 1:
            #     finer effective GSD -> downsample to canonical grid.
            canonical_h = int(
                round(
                    H / s
                )
            )

            canonical_w = int(
                round(
                    W / s
                )
            )

            # Current experiment range gives 128...512 for H=W=256.
            # The guard only prevents invalid pooling dimensions if
            # this module is reused with a much wider scale range.
            canonical_h = max(
                max_kernel,
                canonical_h,
            )

            canonical_w = max(
                max_kernel,
                canonical_w,
            )

            canonical_sizes.append(
                (
                    canonical_h,
                    canonical_w,
                )
            )

            x = dsm[
                b:b+1
            ]

            # Important exact-equivalence path.
            #
            # At s=1 do NOT interpolate at all, so the decomposition
            # is bitwise the same operation as original R4.
            if (
                canonical_h == H
                and canonical_w == W
            ):
                bands, _ = (
                    self.decompose(
                        x
                    )
                )

                output_bands.append(
                    bands
                )

                continue

            canonical = F.interpolate(
                x,
                size=(
                    canonical_h,
                    canonical_w,
                ),
                mode="bilinear",
                align_corners=False,
            )

            bands_canonical, _ = (
                self.decompose(
                    canonical
                )
            )

            # [1,K,C,Hc,Wc]
            # ->
            # [1,K*C,Hc,Wc]
            bands_flat = (
                bands_canonical
                .reshape(
                    1,
                    K * C,
                    canonical_h,
                    canonical_w,
                )
            )

            bands_back = F.interpolate(
                bands_flat,
                size=(
                    H,
                    W,
                ),
                mode="bilinear",
                align_corners=False,
            )

            bands_back = (
                bands_back
                .reshape(
                    1,
                    K,
                    C,
                    H,
                    W,
                )
            )

            output_bands.append(
                bands_back
            )

        self.last_canonical_sizes = tuple(
            canonical_sizes
        )

        return torch.cat(
            output_bands,
            dim=0,
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

        B = optical.shape[0]

        sample_scales = (
            self._take_sample_scales(
                B
            )
        )

        # ----------------------------------------------------
        # Optical:
        # unchanged pixel-coordinate decomposition.
        # ----------------------------------------------------

        optical_bands, _ = (
            self.decompose(
                optical
            )
        )

        # ----------------------------------------------------
        # DSM:
        # physical-coordinate decomposition.
        # ----------------------------------------------------

        dsm_bands = (
            self.physical_dsm_decompose(
                dsm,
                sample_scales,
            )
        )

        # Diagnostics remain identical to R4.
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
            .view(
                1,
                K,
                1,
                1,
            )
            .expand(
                optical.shape[0],
                -1,
                -1,
                -1,
            )
        )

        dsm_weights = (
            weights[1]
            .view(
                1,
                K,
                1,
                1,
            )
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


class VisionTransformerPhysicalDSM(
    VisionTransformerMultiBandVariant
):
    """
    E51-B PH-R4 full model.
    """

    def __init__(
        self,
        config,
        img_size=224,
        num_classes=6,
        zero_head=False,
        vis=False,
        router_mode="modality_static",
    ):
        if router_mode != "modality_static":
            raise ValueError(
                "E51-B Physical DSM currently supports only "
                "router_mode='modality_static'"
            )

        super().__init__(
            config=config,
            img_size=img_size,
            num_classes=num_classes,
            zero_head=zero_head,
            vis=vis,
            router_mode="modality_static",
        )

        hybrid = (
            self
            .transformer
            .embeddings
            .hybrid_model
        )

        # Replace only multiband0.
        #
        # Everything else remains the exact R4 architecture.
        hybrid.multiband0 = (
            PhysicalDSMStaticMultiBandRouter(
                hidden_channels=16,
                kernel_sizes=(
                    3,
                    7,
                    15,
                    31,
                ),
            )
        )

    def set_sample_scales(
        self,
        scales,
    ):
        module = (
            self
            .transformer
            .embeddings
            .hybrid_model
            .multiband0
        )

        module.set_sample_scales(
            scales
        )

    def get_multiband_diagnostics(
        self,
    ):
        out = super().get_multiband_diagnostics()

        module = (
            self
            .transformer
            .embeddings
            .hybrid_model
            .multiband0
        )

        out[
            "physical_sample_scales"
        ] = module.last_sample_scales

        out[
            "physical_canonical_sizes"
        ] = module.last_canonical_sizes

        return out
