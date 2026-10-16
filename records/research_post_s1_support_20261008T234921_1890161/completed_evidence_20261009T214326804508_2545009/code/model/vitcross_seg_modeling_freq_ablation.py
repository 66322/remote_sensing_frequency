# coding=utf-8
"""
Frequency ablation variants for Thesis Chapter-4 NoSR reproduction.

F0: standard bilinear decoder
F1: LFAU only
F2: LFAU + SGOR
F3: LFAU + SGOR + HFDC

IMPORTANT:
- Backbone / Transformer are reused unchanged from the verified F3 implementation.
- F0 bypasses FreqFusion completely.
- F1/F2 use comp_feat_upsample=False because the preserved FreqFusion
  implementation raises NotImplementedError when high-pass is disabled
  under comp_feat_upsample=True.
- F3 is intended to be architecturally compatible with the already verified
  Thesis_Ch4_NoSR_v1 F3 model.
"""

import copy
import numpy as np
import torch
import torch.nn as nn

from model import vitcross_seg_modeling_freqfusion as base


VALID_VARIANTS = ("F0", "F1", "F2", "F3")


class DecoderBlockFreqAblation(nn.Module):
    def __init__(
        self,
        in_channels,
        out_channels,
        skip_channels=0,
        use_batchnorm=True,
        compressed_channels=64,
        freq_variant="F3",
    ):
        super().__init__()

        freq_variant = str(freq_variant).upper()

        if freq_variant not in VALID_VARIANTS:
            raise ValueError(
                f"Unknown freq_variant={freq_variant}; "
                f"expected one of {VALID_VARIANTS}"
            )

        self.freq_variant = freq_variant
        self.skip_channels = skip_channels

        # F0 has no frequency module at all.
        self.use_freq_fusion = (
            freq_variant != "F0"
            and skip_channels > 0
        )

        if self.use_freq_fusion:
            if freq_variant == "F1":
                # LFAU only
                ff_kwargs = dict(
                    feature_resample=False,
                    use_high_pass=False,
                    use_low_pass=True,
                    comp_feat_upsample=False,
                )

            elif freq_variant == "F2":
                # LFAU + SGOR
                ff_kwargs = dict(
                    feature_resample=True,
                    use_high_pass=False,
                    use_low_pass=True,
                    comp_feat_upsample=False,
                )

            elif freq_variant == "F3":
                # LFAU + SGOR + HFDC
                # Same intended setting as the verified current F3.
                ff_kwargs = dict(
                    feature_resample=True,
                    use_high_pass=True,
                    use_low_pass=True,
                    comp_feat_upsample=True,
                )

            self.freq_fusion = base.FreqFusion(
                hr_channels=skip_channels,
                lr_channels=in_channels,
                compressed_channels=compressed_channels,
                hr_residual=True,
                semi_conv=True,
                hamming_window=True,
                **ff_kwargs,
            )

        self.conv1 = base.Conv2dReLU(
            in_channels + skip_channels,
            out_channels,
            kernel_size=3,
            padding=1,
            use_batchnorm=use_batchnorm,
        )

        self.conv2 = base.Conv2dReLU(
            out_channels,
            out_channels,
            kernel_size=3,
            padding=1,
            use_batchnorm=use_batchnorm,
        )

        self.up = nn.UpsamplingBilinear2d(
            scale_factor=2
        )

    def forward(self, x, skip=None):
        if skip is not None:
            if (
                self.use_freq_fusion
                and self.skip_channels > 0
            ):
                _, skip, x = self.freq_fusion(
                    hr_feat=skip,
                    lr_feat=x,
                )
            else:
                # F0: ordinary decoder upsampling
                x = self.up(x)

            x = torch.cat(
                [x, skip],
                dim=1,
            )

        else:
            # Final decoder block has no skip.
            x = self.up(x)

        x = self.conv1(x)
        x = self.conv2(x)

        return x


class DecoderCupFreqAblation(nn.Module):
    def __init__(
        self,
        config,
        freq_variant="F3",
    ):
        super().__init__()

        self.config = config
        self.freq_variant = freq_variant

        head_channels = 512

        self.conv_more = base.Conv2dReLU(
            config.hidden_size,
            head_channels,
            kernel_size=3,
            padding=1,
            use_batchnorm=True,
        )

        decoder_channels = list(
            config.decoder_channels
        )

        in_channels = (
            [head_channels]
            + decoder_channels[:-1]
        )

        out_channels = decoder_channels

        if config.n_skip != 0:
            # Copy to avoid mutating shared config.
            skip_channels = list(
                config.skip_channels
            )

            for i in range(
                4 - config.n_skip
            ):
                skip_channels[3 - i] = 0

        else:
            skip_channels = [0, 0, 0, 0]

        blocks = []

        for in_ch, out_ch, sk_ch in zip(
            in_channels,
            out_channels,
            skip_channels,
        ):
            blocks.append(
                DecoderBlockFreqAblation(
                    in_channels=in_ch,
                    out_channels=out_ch,
                    skip_channels=sk_ch,
                    use_batchnorm=True,
                    compressed_channels=64,
                    freq_variant=freq_variant,
                )
            )

        self.blocks = nn.ModuleList(
            blocks
        )

    def forward(
        self,
        hidden_states,
        features=None,
    ):
        B, n_patch, hidden = (
            hidden_states.size()
        )

        h = int(np.sqrt(n_patch))
        w = int(np.sqrt(n_patch))

        x = hidden_states.permute(
            0, 2, 1
        )

        x = x.contiguous().view(
            B,
            hidden,
            h,
            w,
        )

        x = self.conv_more(x)

        for i, decoder_block in enumerate(
            self.blocks
        ):
            if features is not None:
                skip = (
                    features[i]
                    if i < self.config.n_skip
                    else None
                )
            else:
                skip = None

            x = decoder_block(
                x,
                skip=skip,
            )

        return x


class VisionTransformerFreqAblation(nn.Module):
    def __init__(
        self,
        config,
        img_size=224,
        num_classes=21843,
        zero_head=False,
        vis=False,
        freq_variant="F3",
    ):
        super().__init__()

        freq_variant = str(
            freq_variant
        ).upper()

        if freq_variant not in VALID_VARIANTS:
            raise ValueError(
                freq_variant
            )

        self.num_classes = num_classes
        self.zero_head = zero_head
        self.classifier = config.classifier
        self.freq_variant = freq_variant

        # Backbone/Transformer is exactly the existing implementation.
        self.transformer = base.Transformer(
            config,
            img_size,
            vis,
        )

        self.decoder = (
            DecoderCupFreqAblation(
                config,
                freq_variant=freq_variant,
            )
        )

        self.segmentation_head = (
            base.SegmentationHead(
                in_channels=
                    config["decoder_channels"][-1],
                out_channels=
                    config["n_classes"],
                kernel_size=3,
            )
        )

        self.config = config

    def forward(self, x, y):
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

        x = self.decoder(
            x,
            features,
        )

        logits = (
            self.segmentation_head(x)
        )

        return logits

    # Reuse the already verified pretrained-weight loading logic.
    load_from = (
        base.VisionTransformerFreqFusion.load_from
    )


CONFIGS = base.CONFIGS
