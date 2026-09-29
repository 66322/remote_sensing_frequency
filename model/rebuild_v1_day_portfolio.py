"""Post-D21 A/B/C/D/E models. All candidates here are prospective designs."""
import torch
from torch import nn
from torch.nn import functional as F

from model.rebuild_v1_d21_detail import DetailDinoSegmenter, detail_channels
from model.rebuild_v1_night_screen import FrozenDinoSegmenter


def last_four_trainable(encoder):
    for p in encoder.parameters():
        p.requires_grad_(False)
    blocks = getattr(encoder, 'blocks', None)
    if blocks is None or len(blocks) < 4:
        raise RuntimeError('DINO encoder has fewer than four blocks')
    for block in blocks[-4:]:
        for p in block.parameters():
            p.requires_grad_(True)


def encoded_features(model, rgb):
    h, w = rgb.shape[-2:]
    image = F.pad((rgb-model.mean)/model.std,
                  (0, (-w) % 14, 0, (-h) % 14), mode='replicate')
    # Do not use no_grad here: C/D need CE gradients through frozen early blocks.
    tokens = model.encoder.forward_features(image)['x_norm_patchtokens']
    return tokens.transpose(1, 2).reshape(len(rgb), 384, image.shape[-2]//14, image.shape[-1]//14)


class AContinuation(DetailDinoSegmenter):
    def __init__(self, encoder, arm, last4):
        super().__init__(encoder, arm)
        if last4:
            last_four_trainable(self.encoder)

    def forward(self, rgb, aux):
        h, w = rgb.shape[-2:]
        features = encoded_features(self, rgb)
        features = F.interpolate(self.rgb(features), size=((h+3)//4, (w+3)//4), mode='nearest')
        if self.detail is not None:
            features = features + self.detail(detail_channels(aux, self.arm))
        return F.interpolate(self.decoder(features), size=(h, w), mode='nearest')


class ConditionalResidual(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Conv2d(130, 32, 3, padding=1),
            nn.GroupNorm(4, 32), nn.GELU(), nn.Conv2d(32, 128, 1))
        nn.init.zeros_(self.net[-1].weight)
        nn.init.zeros_(self.net[-1].bias)

    def forward(self, rgb_feature, channels):
        return self.net(torch.cat((rgb_feature, channels), dim=1))


def auxiliary_channels(aux, arm):
    if arm == 'B1' or arm == 'D_gray':
        # Caller supplies RGB grayscale as aux for these capacity controls.
        arm = 'M1'
    elif arm == 'B2':
        arm = 'M0'
    elif arm in ('B3', 'D_dsm'):
        arm = 'F2'
    elif arm == 'B4':
        arm = 'F3'
    return detail_channels(aux, arm)


class BAnchoredResidual(FrozenDinoSegmenter):
    def __init__(self, encoder, arm):
        if arm not in ('B1', 'B2', 'B3', 'B4'):
            raise ValueError(arm)
        super().__init__(encoder, auxiliary=False)
        self.arm = arm
        self.residual = ConditionalResidual()
        for module in (self.rgb, self.decoder):
            for p in module.parameters():
                p.requires_grad_(False)

    def forward(self, rgb, aux):
        h, w = rgb.shape[-2:]
        with torch.no_grad():
            feature = F.interpolate(self.rgb(encoded_features(self, rgb)),
                size=((h+3)//4, (w+3)//4), mode='nearest')
        mask = (aux.abs().flatten(1).sum(1) > 0).to(feature.dtype)[:, None, None, None]
        residual = self.residual(feature, auxiliary_channels(aux, self.arm)) * mask
        return F.interpolate(self.decoder(feature + residual), size=(h, w), mode='nearest')


class RestorationFront(nn.Module):
    def __init__(self):
        super().__init__()
        self.net = nn.Sequential(nn.Conv2d(3, 32, 3, padding=1),
            nn.GELU(), nn.Conv2d(32, 32, 3, padding=1), nn.GELU(), nn.Conv2d(32, 3, 3, padding=1))
        nn.init.zeros_(self.net[-1].weight)
        nn.init.zeros_(self.net[-1].bias)

    def forward(self, x):
        return x + self.net(x)


def low_resolution_view(rgb, scale, blur_sigma=0.):
    if scale not in (2, 4):
        raise ValueError(scale)
    h, w = rgb.shape[-2:]
    if blur_sigma:
        radius = max(1, int(round(3*blur_sigma)))
        t = torch.arange(-radius, radius+1, device=rgb.device, dtype=rgb.dtype)
        kernel = torch.exp(-0.5*(t/blur_sigma)**2)
        kernel = kernel/kernel.sum()
        k = torch.outer(kernel, kernel)
        rgb = F.conv2d(F.pad(rgb, (radius,)*4, mode='replicate'),
                       k[None, None].expand(3, 1, -1, -1), groups=3)
    lr = F.interpolate(rgb, size=(h//scale, w//scale), mode='area')
    return F.interpolate(lr, size=(h, w), mode='bicubic', align_corners=False)


def highpass(x):
    return x-F.avg_pool2d(F.pad(x, (2, 2, 2, 2), mode='replicate'), 5, 1)


class CDRestorationSegmenter(FrozenDinoSegmenter):
    def __init__(self, encoder, arm, scale):
        if arm not in ('C0', 'C1', 'C2', 'C3', 'D_ce_dsm', 'D_ph_dsm', 'D_ph_gray'):
            raise ValueError(arm)
        super().__init__(encoder, auxiliary=False)
        last_four_trainable(self.encoder)
        self.arm, self.scale, self.blur_sigma = arm, scale, 0.
        self.front = None if arm == 'C0' else RestorationFront()
        self.residual = ConditionalResidual() if arm.startswith('D_') else None

    def forward_with_restored(self, rgb, aux, scale=None, blur_sigma=0.):
        h, w = rgb.shape[-2:]
        restored = low_resolution_view(rgb, scale or self.scale, blur_sigma or self.blur_sigma)
        if self.front is not None:
            restored = self.front(restored)
        feature = F.interpolate(self.rgb(encoded_features(self, restored)),
            size=((h+3)//4, (w+3)//4), mode='nearest')
        if self.residual is not None:
            feature = feature + self.residual(feature,
                auxiliary_channels(aux, 'D_gray' if self.arm == 'D_ph_gray' else 'D_dsm'))
        logits = F.interpolate(self.decoder(feature), size=(h, w), mode='nearest')
        return logits, restored

    def forward(self, rgb, aux):
        return self.forward_with_restored(rgb, aux)[0]
