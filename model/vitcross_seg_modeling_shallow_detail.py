"""
P2-H + final shallow-detail preservation.

Two controlled variants:

NORMAL:
    final decoder feature receives the full shallow fused feature.

HF:
    final decoder feature receives only the local HF residual:
        H = F - AvgPool3x3(F)

Both variants:
    - use exactly the same source feature;
    - use exactly the same injection location;
    - use exactly the same learnable projection;
    - have exactly the same parameter count;
    - zero-init the projection, therefore step-0 output is
      exactly the original P2-H output.

The source feature is features[-1]:
    64 channels, input/2 resolution,
    after P2-H HF reliability calibration and SE0 fusion.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

from model.vitcross_seg_modeling_hf_reliability_detpair import (
    VisionTransformerHFReliability,
)


class VisionTransformerShallowDetail(
    VisionTransformerHFReliability
):
    VALID_DETAIL_MODES = {
        "NORMAL",
        "HF",
    }

    def __init__(
        self,
        config,
        img_size=224,
        num_classes=6,
        zero_head=False,
        vis=False,
        detail_mode="NORMAL",
    ):
        # Build the exact original P2-H first.
        super().__init__(
            config=config,
            img_size=img_size,
            num_classes=num_classes,
            zero_head=zero_head,
            vis=vis,
        )

        detail_mode = str(
            detail_mode
        ).upper()

        if (
            detail_mode
            not in self.VALID_DETAIL_MODES
        ):
            raise ValueError(
                f"Unknown detail_mode: "
                f"{detail_mode}"
            )

        self.detail_mode = detail_mode

        # ----------------------------------------------------
        # IMPORTANT SEED-FAIRNESS DETAIL
        #
        # nn.Conv2d normally consumes Torch RNG during its
        # default initialization, even though we immediately
        # zero-init it.
        #
        # Save + restore the RNG state so adding this branch
        # does NOT shift subsequent dropout/training RNG
        # relative to the original P2-H baseline.
        # ----------------------------------------------------
        cpu_rng = torch.get_rng_state()

        cuda_rng = None

        if torch.cuda.is_available():
            cuda_rng = (
                torch.cuda
                .get_rng_state_all()
            )

        shallow_channels = 64

        decoder_out_channels = int(
            config.decoder_channels[-1]
        )

        # Put it under decoder.* deliberately:
        # the existing trainer therefore assigns it to the
        # already verified decoder/head 10x LR group.
        self.decoder.detail_proj = nn.Conv2d(
            shallow_channels,
            decoder_out_channels,
            kernel_size=1,
            stride=1,
            padding=0,
            bias=True,
        )

        nn.init.zeros_(
            self.decoder
            .detail_proj
            .weight
        )

        if (
            self.decoder
            .detail_proj
            .bias
            is not None
        ):
            nn.init.zeros_(
                self.decoder
                .detail_proj
                .bias
            )

        # Restore RNG state consumed by Conv2d construction.
        torch.set_rng_state(
            cpu_rng
        )

        if cuda_rng is not None:
            torch.cuda.set_rng_state_all(
                cuda_rng
            )

        self.last_detail_source_abs = None
        self.last_detail_residual_abs = None

    def _detail_source(
        self,
        shallow,
    ):
        if self.detail_mode == "NORMAL":
            return shallow

        # HF variant:
        # local high-frequency residual.
        #
        # count_include_pad=False avoids an artificial border
        # HF response caused only by zero padding.
        low = F.avg_pool2d(
            shallow,
            kernel_size=3,
            stride=1,
            padding=1,
            count_include_pad=False,
        )

        return shallow - low

    def forward(
        self,
        x,
        y,
    ):
        (
            x,
            y,
            attn_weights,
            features,
        ) = self.transformer(
            x,
            y,
        )

        x = x + y

        # Original F0 decoder, unchanged.
        x = self.decoder(
            x,
            features,
        )

        if (
            features is None
            or len(features) < 3
        ):
            raise RuntimeError(
                "Expected P2-H hybrid "
                "features with 3 skip levels."
            )

        # features after backbone reversal:
        #
        #   features[0] : 512 ch @ input/8
        #   features[1] : 256 ch @ input/4
        #   features[2] :  64 ch @ input/2
        #
        # Use only the shallowest fused representation.
        shallow = features[-1]

        if shallow.shape[1] != 64:
            raise RuntimeError(
                "Unexpected shallow feature "
                f"shape: {tuple(shallow.shape)}"
            )

        detail_source = (
            self._detail_source(
                shallow
            )
        )

        detail = (
            self.decoder
            .detail_proj(
                detail_source
            )
        )

        # 256 -> 512 for the current crop=512 setup.
        if (
            detail.shape[-2:]
            != x.shape[-2:]
        ):
            detail = F.interpolate(
                detail,
                size=x.shape[-2:],
                mode="bilinear",
                align_corners=False,
            )

        # Zero-init residual endpoint:
        # initial x is EXACTLY the baseline decoder x.
        x = x + detail

        self.last_detail_source_abs = (
            detail_source
            .detach()
            .abs()
            .mean()
        )

        self.last_detail_residual_abs = (
            detail
            .detach()
            .abs()
            .mean()
        )

        logits = (
            self.segmentation_head(x)
        )

        return logits

    def get_detail_diagnostics(self):
        return {
            "mode": self.detail_mode,
            "source_abs": (
                self.last_detail_source_abs
            ),
            "residual_abs": (
                self.last_detail_residual_abs
            ),
        }

    # Preserve original P2-H pretrained loader.
    load_from = (
        VisionTransformerHFReliability
        .load_from
    )
