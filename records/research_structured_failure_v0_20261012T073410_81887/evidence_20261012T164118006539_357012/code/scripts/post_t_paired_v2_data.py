"""Inherited stateless sample RNG; variable stop age and exact CPU batch hashes."""
import hashlib
import json
import torch
from post_d30_data import Crops as OriginalCrops


class Crops(OriginalCrops):
    def __init__(self, tiles, ids, augmentation, plan, job, start=0):
        super().__init__(tiles, ids, augmentation, plan, start, job)
        self.stop = job['steps']


def batch_digest(batch):
    h = hashlib.sha256()
    for name in sorted(batch):
        value = batch[name]
        h.update(name.encode())
        if torch.is_tensor(value):
            value = value.detach().cpu().contiguous()
            h.update(str(value.dtype).encode())
            h.update(str(tuple(value.shape)).encode())
            h.update(value.numpy().tobytes())
        else:
            h.update(json.dumps(value, sort_keys=True, separators=(',', ':')).encode())
    return h.hexdigest()


class BatchLedger:
    """One digest per actual materialized batch; compare the common prefix online."""
    def __init__(self, out, peers, start=0):
        self.path = out / 'batch_hashes.jsonl'
        self.peers = [(p, p.open(encoding='utf-8')) for p in peers]
        self.chain = hashlib.sha256()
        self.steps = 0
        self.prefixes = {}
        if self.path.exists():
            with self.path.open(encoding='utf-8') as f:
                for line in f:
                    row = json.loads(line)
                    self.steps += 1
                    if row['step'] != self.steps:
                        raise RuntimeError('noncontiguous existing batch ledger')
                    self.chain.update(bytes.fromhex(row['sha256']))
                    if self.steps % 4000 == 0:
                        self.prefixes[str(self.steps)] = self.chain.hexdigest()
            if self.steps != start:
                raise RuntimeError('ledger/checkpoint age mismatch; no implicit rollback')
        elif start:
            raise RuntimeError('resume ledger missing')
        for _, stream in self.peers:
            for _ in range(start):
                if not stream.readline():
                    break
        self.handle = self.path.open('a' if self.path.exists() else 'x', encoding='utf-8')

    def record(self, step, batch):
        if step != self.steps + 1:
            raise RuntimeError('noncontiguous sample stream')
        digest = batch_digest(batch)
        for path, stream in self.peers:
            line = stream.readline()
            if line:
                row = json.loads(line)
                if row != dict(step=step, sha256=digest):
                    raise RuntimeError('paired batch differs from ' + str(path))
        self.handle.write(json.dumps(dict(step=step, sha256=digest)) + '\n')
        self.handle.flush()
        self.chain.update(bytes.fromhex(digest))
        self.steps = step
        if step % 4000 == 0:
            self.prefixes[str(step)] = self.chain.hexdigest()

    def close(self):
        self.handle.close()
        for _, stream in self.peers:
            stream.close()
        return dict(steps=self.steps, prefixes=self.prefixes, actual_cpu_tensors_hashed=True,
                    rng='inherited keyed sample/augmentation RNG, independent of model RNG')
