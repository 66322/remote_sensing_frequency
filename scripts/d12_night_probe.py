"""D12 CPU-only matched three-outcome probes. Labels form targets, never inputs."""
import hashlib
import json
from pathlib import Path

import numpy as np
import torch
from scipy.optimize import minimize_scalar
from d11_benefit_probe import FREQUENCY, expert_features, targets, choose_threshold

ROOT = Path("/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro")
CFG = ROOT / "configs/rebuild_v1/d12_night_20260923.json"
D11 = ROOT / "records/rebuild_v1_d11_benefit_probe_20260923"
D10 = ROOT / "records/rebuild_v1_d10m_mechanism_20260923"
BASE = ROOT / "records/rebuild_v1_d12_night_20260923"
MODELS = ("E", "Ecap", "ES", "EF", "ESF", "ESF_shuffleS", "ESF_shuffleF")


def read_npz(path):
    with np.load(path, allow_pickle=False) as data:
        return {key: data[key].copy() for key in data.files}


def sample_and_semantic(seed, tile, condition, role, smoke=False):
    if role == "evaluation":
        source = D10 / f"seed{seed}_{condition}" / f"samples_{tile}.npz"
    else:
        source = D11 / "development" / f"seed{seed}_{tile}" / f"{condition}.npz"
    semantic_folder = BASE / "semantic" / f"seed{seed}_{tile}_{condition}{'_smoke' if smoke else ''}"
    meta = json.loads((semantic_folder / "summary.json").read_text())
    sem_path = semantic_folder / "semantic.npz"
    if (meta["seed"] != seed or meta["tile"] != tile or meta["condition"] != condition or
            meta["role"] != role or meta["smoke"] != smoke or meta["test6_loaded"] or
            meta["source_sha256"] != hashlib.sha256(source.read_bytes()).hexdigest() or
            meta["semantic_sha256"] != hashlib.sha256(sem_path.read_bytes()).hexdigest() or
            meta["config_sha256"] != hashlib.sha256(CFG.read_bytes()).hexdigest()):
        raise RuntimeError("D12 semantic/source manifest mismatch")
    sample, sem = read_npz(source), read_npz(sem_path)
    if smoke:
        n = meta["sample_n"]
        sample = {k: v[:, :n] if k in ("rgb_prob", "dual_prob") else v[:n] for k, v in sample.items()}
    if not (np.array_equal(sample["yy"], sem["yy"]) and np.array_equal(sample["xx"], sem["xx"])):
        raise RuntimeError("D12 pixel alignment failed")
    return sample, sem, meta


def features(sample, sem, model, seed, tile, condition):
    expert, _, _ = expert_features(sample)
    parts = [expert]
    uses_semantic = model in ("ES", "ESF", "ESF_shuffleS", "ESF_shuffleF")
    uses_frequency = model in ("EF", "ESF", "ESF_shuffleS", "ESF_shuffleF")
    rng = np.random.default_rng(int.from_bytes(hashlib.sha256(
        f"D12:{seed}:{tile}:{condition}:{model}".encode()).digest()[:8], "little"))
    if uses_semantic:
        semantic = np.concatenate([sem["sem_rgb"].T, sem["sem_dual"].T], axis=1)
        if model == "ESF_shuffleS":
            semantic = semantic[rng.permutation(len(semantic))]
        parts.append(semantic)
    if uses_frequency:
        frequency = np.column_stack([np.log1p(np.maximum(sample[k], 0)*10000)
                                     if "energy" in k else sample[k] for k in FREQUENCY])
        if model == "ESF_shuffleF":
            frequency = frequency[rng.permutation(len(frequency))]
        parts.append(frequency)
    x = np.column_stack(parts).astype(np.float32)
    if not np.isfinite(x).all():
        raise RuntimeError("nonfinite D12 feature")
    return x


class Head(torch.nn.Module):
    def __init__(self, n, model):
        super().__init__()
        width = 256 if model == "Ecap" else 64
        self.layers = torch.nn.Sequential(torch.nn.Linear(n, width), torch.nn.ReLU(),
                                          torch.nn.Linear(width, 3))

    def forward(self, x):
        return self.layers(x)


def train_model(x, y, model_name, seed, cfg):
    torch.set_num_threads(2)
    torch.manual_seed(20260923 + seed)
    mean = x.mean(0)
    scale = np.maximum(x.std(0), 1e-6)
    scaled = np.ascontiguousarray((x - mean) / scale, np.float32)
    if min(np.bincount(y, minlength=3)) < 20:
        raise RuntimeError("too few examples of a target outcome")
    head = Head(x.shape[1], model_name)
    optimizer = torch.optim.AdamW(head.parameters(), lr=cfg["learning_rate"],
                                  weight_decay=cfg["weight_decay"])
    tx, ty = torch.from_numpy(scaled), torch.from_numpy(y.astype(np.int64))
    for epoch in range(cfg["epochs"]):
        generator = torch.Generator().manual_seed(12000 + seed * 100 + epoch)
        for ids in torch.randperm(len(ty), generator=generator).split(cfg["batch_size"]):
            optimizer.zero_grad(set_to_none=True)
            loss = torch.nn.functional.cross_entropy(head(tx[ids]), ty[ids])
            if not torch.isfinite(loss):
                raise RuntimeError("nonfinite D12 loss")
            loss.backward()
            optimizer.step()
    return dict(mean=mean.tolist(), scale=scale.tolist(),
                state={k: v.detach().numpy().tolist() for k, v in head.state_dict().items()},
                parameter_count=sum(p.numel() for p in head.parameters()),
                input_features=x.shape[1], model=model_name, seed=seed, temperature=1.)


def raw_logits(artifact, x, batch=65536):
    head = Head(artifact["input_features"], artifact["model"])
    head.load_state_dict({k: torch.tensor(v, dtype=torch.float32) for k, v in artifact["state"].items()})
    head.eval()
    mean, scale = np.asarray(artifact["mean"], np.float32), np.asarray(artifact["scale"], np.float32)
    out = []
    with torch.inference_mode():
        for a in range(0, len(x), batch):
            z = torch.from_numpy(np.ascontiguousarray((x[a:a+batch] - mean) / scale, np.float32))
            out.append(head(z).numpy())
    return np.concatenate(out)


def predict(artifact, x):
    logits = raw_logits(artifact, x) / artifact["temperature"]
    logits -= logits.max(axis=1, keepdims=True)
    ex = np.exp(logits)
    return ex / ex.sum(axis=1, keepdims=True)


def temperature(artifact, x, y):
    from scipy.special import logsumexp
    logits = raw_logits(artifact, x)
    def objective(t):
        z = logits / t
        return float(np.mean(logsumexp(z, axis=1) - z[np.arange(len(y)), y]))
    fit = minimize_scalar(objective, bounds=(.25, 4.), method="bounded")
    if not fit.success:
        raise RuntimeError("temperature calibration failed")
    return float(fit.x)
