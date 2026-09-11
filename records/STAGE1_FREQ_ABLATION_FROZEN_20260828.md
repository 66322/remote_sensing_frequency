# Stage-1 Frequency Ablation Frozen

Date: 2026-08-28

## Status

Formal acceptance completed.

### Vaihingen

- F0: no frequency module
- F1: LFAU
- F2: LFAU + SGOR
- F3: LFAU + SGOR + HFDC
- seed: 42
- crop: 256
- batch: 8
- optimizer: SGD
- total steps: 50000
- selection: best noBoundary OA checkpoint
- all evaluation histories and diagnostic best checkpoints retained

Primary noBoundary mIoU:

- F0: 82.1171%
- F1: 81.8533%
- F2: 81.9656%
- F3: 82.1908%

F3 - F0 = +0.0737 pp

### Potsdam

Same F0-F3 protocol.

Primary noBoundary mIoU:

- F0: 82.5337%
- F1: 82.3022%
- F2: 82.6806%
- F3: 82.8011%

F3 - F0 = +0.2674 pp

Potsdam formal acceptance:
Overall PASS

## Interpretation

Stage-1 results are immutable baseline evidence.

The next stage investigates whether a FreqFusion-like training
recipe increases the marginal gain of the complete frequency decoder.

Stage-2 does NOT overwrite or replace Stage-1 results.
