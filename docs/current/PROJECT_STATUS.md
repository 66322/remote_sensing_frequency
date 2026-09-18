# Current Project Status

- Updated: 2026-09-18
- Active branch: `rebuild-v1-protocol-20260915`
- Current line: REBUILD_V1 multimodal capacity and robustness audit
- Dataset: ISPRS Potsdam
- Development split: Train16 / Val2
- Val2 tiles: `3_11`, `5_10`
- Historical TEST6: prohibited for training, checkpoint selection and current diagnostics
- Formal seed: 42
- Formal schedule: 16000 optimizer steps
- Selection metric: Val2 NoBoundary mIoU_fg5

## Completed core results

| ID | Meaning | FullGT mIoU_fg5 | NB mIoU_fg5 | Status |
|---|---|---:|---:|---|
| R01 | true Optical-only | 80.6883 | 85.3713 | complete |
| R02 | clean Optical+DSM | 81.8483 | 86.2016 | complete |
| R03 | quality-corruption training Q | 82.1069 | 86.5251 | complete |
| R04 | modality-dropout training D | 81.6042 | 85.9818 | complete |
| C-OO | Optical+Optical capacity control | 81.8281 | 86.3548 | complete |
| R05 | Optical+DSM with Q+D | 82.5147 | 87.0485 | complete |
| C-OO-QD | Optical+Optical with matched Q+D | 81.6670 | 86.1969 | complete |

These are seed42 results on the two-tile Val2 development split. They are not
multi-seed or held-out test conclusions.

## Current evidence

- R05 exceeds matched C-OO-QD by about 0.8517 pp NB mIoU_fg5 on clean Val2.
- R05 remains stronger under second-stream blur/down2/down4/down8.
- Under down8, R05 exceeds the matched C-OO-QD condition by about 6.1502 pp.
- With DSM completely zeroed, R05 reaches 83.1294 NB mIoU_fg5, below R01 at 85.3713.
- C-OO clean exceeds R02 clean, so the entire R02-R01 difference cannot be
  attributed to DSM-specific information.
- Optical-zero is not an equivalent semantic comparison between R05 and
  C-OO-QD and must not be used as direct DSM-value evidence.

## Current conclusion boundary

Supported:

- Q+D is a strong robustness baseline.
- DSM provides condition-dependent value beyond a matched second-stream
  capacity control under several degradation conditions.
- A fallback gap remains under complete DSM absence.

Not supported:

- DSM is beneficial under every condition.
- A new frequency module has beaten simple robust training.
- The current single-seed two-tile evidence is a final test-set conclusion.

## Active work

The only active experiment is D1-D3 local failure diagnostics comparing R05
and C-OO-QD on Val2 without retraining.
