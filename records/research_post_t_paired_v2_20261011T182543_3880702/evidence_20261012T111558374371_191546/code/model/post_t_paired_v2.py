"""Frozen S1-0 safety path plus privately adapted RGB features and fusion."""
import copy
import hashlib
import torch
from torch.nn import functional as F
from model.post_s1_transfer_model import PrivateDecoder


def intervene(feature, mode):
    if mode == 'C':
        return feature
    if mode == 'Z':
        return torch.zeros_like(feature)
    if mode == 'S':
        return torch.roll(feature, (feature.shape[-2] // 2, feature.shape[-1] // 2), (-2, -1))
    raise ValueError('unregistered DSM intervention')


class PairedAdaptation(PrivateDecoder):
    def __init__(self, rgb_expert, dsm_expert, job, path, digest):
        super().__init__(rgb_expert, dsm_expert, job, path, digest,
                         dict(path=path, sha256=digest))
        self.private_rgb = copy.deepcopy(self.rgb_expert)
        # N1 taps are unused in this late-feature path. Copied closures would
        # otherwise write private activations into the original N1 tap cache.
        for block in self.private_rgb.net.encoder.blocks:
            block._forward_hooks.clear()
        self.private_rgb.requires_grad_(False)
        if job['mechanism'] in ('H', 'R'):
            self.private_rgb.net.rgb.requires_grad_(True)
            self.private_rgb.net.decoder[:-1].requires_grad_(True)
        if job['mechanism'] == 'R':
            for block in self.private_rgb.net.encoder.blocks[-4:]:
                block.requires_grad_(True)
        if job['mechanism'] not in ('F', 'H', 'R'):
            raise ValueError('reserved/unregistered arm')
        self.private_rgb.net.decoder[-1].requires_grad_(False)
        self.dsm_intervention = 'C'
        self.train(False)

    def train(self, mode=True):
        super().train(mode)
        if hasattr(self, 'private_rgb'):
            self.private_rgb.train(mode and self.job['mechanism'] != 'F')
        return self

    def forward(self, rgb, dsm, rm, dm, return_parts=False):
        if rm.dtype != torch.bool or dm.dtype != torch.bool or rm.shape != dsm.shape or dm.shape != dsm.shape:
            raise ValueError('aligned boolean masks required')
        rgb = rgb.masked_fill(~rm[:, None], 0)
        dsm = dsm.masked_fill(~dm, 0)
        window = rm.flatten(1).any(1) & dm.flatten(1).any(1)
        shape = tuple((s + 3) // 4 for s in rgb.shape[-2:])
        self.taps = {'rgb': {}, 'dsm': {}}
        with torch.no_grad():
            rlog, rf = self.rgb_expert(rgb, dsm)
            dlog, df = self.dsm_expert(rgb, dsm)
            r = self.pyramid('rgb', rf, rgb, rm, shape)
            d = self.pyramid('dsm', df, rgb, dm, shape)
            raw = F.interpolate(self.fusion(torch.cat((r, d, r, d), 1)), rgb.shape[-2:], mode='nearest')
            valid = rm | dm
            z0 = torch.where((rm & dm)[:, None], raw,
                             torch.where(rm[:, None], rlog, dlog)).masked_fill(~valid[:, None], 0)
        self.taps = {'rgb': {}, 'dsm': {}}
        # Keep the same logical three-expert-forward graph in F/H/R.
        _, private_rf = self.private_rgb(rgb, dsm)
        br = torch.where(window[:, None, None], torch.ones_like(rm), rm)
        bd = torch.where(window[:, None, None], torch.ones_like(dm), dm)
        r = self.branch_pyramid('rgb', private_rf, br, shape)
        d = self.branch_pyramid('dsm', intervene(df, self.dsm_intervention), bd, shape)
        branch = F.interpolate(self.branch['fusion'](torch.cat((r, d, r, d), 1)), rgb.shape[-2:], mode='nearest')
        support = (~rm) & dm & window[:, None, None]
        result = torch.where(support[:, None], branch, z0).masked_fill(~valid[:, None], 0)
        self.exposure = dict(residual_support_pixels=int(support.sum()), moved_tokens=0,
                             total_tokens=r.shape[0] * r.shape[-2] * r.shape[-1])
        parts = dict(logits=result, rgb=rlog, dsm=dlog, raw=raw, valid=valid,
                     base_logits=z0, residual_support=support)
        return parts if return_parts else result


def frozen_digest(model):
    """Include all buffers and every parameter declared frozen, including private RGB."""
    trainable = {n for n, p in model.named_parameters() if p.requires_grad}
    h = hashlib.sha256()
    for n, value in model.state_dict().items():
        if n not in trainable:
            h.update(n.encode())
            h.update(str(value.dtype).encode())
            h.update(str(tuple(value.shape)).encode())
            h.update(value.detach().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def optimizer_for(model, cfg):
    groups = []
    for encoder, lr in ((True, cfg['encoder_last4_lr']), (False, cfg['head_lr'])):
        pairs = [(n, p) for n, p in model.named_parameters() if p.requires_grad
                 and n.startswith('private_rgb.net.encoder.blocks.') == encoder]
        if pairs:
            groups.append(dict(params=[p for n, p in pairs], names=[n for n, p in pairs],
                               lr=lr, initial_lr=lr))
    return torch.optim.AdamW(groups, betas=tuple(cfg['betas']), weight_decay=cfg['weight_decay'])


def lr_factor(step, budget):
    if budget not in (8000, 16000) or not 1 <= step <= budget:
        raise ValueError('invalid fixed training age')
    return .1 + .9 * step / 100 if step <= 100 else (budget - step) / (budget - 100)
