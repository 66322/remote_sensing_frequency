# Experiment Report: R05 Quality Plus Modality-Dropout Baseline

## Basic information

- experiment ID: R05
- status: complete
- started at: 2026-09-18T02:26:29+08:00
- completed at: 2026-09-18T08:24:30+08:00
- source Git commit: 3715c6b945897ce45c035ef5ed7f1f117b3f2cbc
- seed: 42
- schedule: 16000 optimizer steps
- best step: 16000
- historical TEST6 loaded: false

## Purpose

Test whether the combination of ordinary quality-corruption training and
modality dropout provides a strong robustness baseline before developing a
more complex reliability or frequency mechanism.

## Main clean result

| Metric | Result |
|---|---:|
| FullGT mIoU_fg5 | 82.5147 |
| NoBoundary mIoU_fg5 | 87.0485 |

## NoBoundary robustness

| Condition | mIoU_fg5 | Drop from clean |
|---|---:|---:|
| clean | 87.0486 | 0.0000 pp |
| DSM blur5 | 86.8219 | 0.2267 pp |
| DSM down2 | 86.8970 | 0.1516 pp |
| DSM down4 | 86.4557 | 0.5928 pp |
| DSM down8 | 85.5023 | 1.5463 pp |
| DSM zero | 83.1294 | 3.9191 pp |

## Conclusion

R05 is the current strongest simple robustness baseline. It is stable under
mild and severe DSM quality degradation, but complete DSM absence still falls
below true Optical-only R01 at 85.3713.

Any proposed new robustness mechanism must compare against R05 rather than only
against clean R02.

## Limitations

Single seed and two validation tiles. The results are development evidence, not
held-out test conclusions.

## Artifacts

- `configs/rebuild_v1/r05_quality_plus_dropout_16k.json`
- `scripts/train_rebuild_v1_r05_quality_plus_dropout.py`
- `records/rebuild_v1_r05_formal_16k_20260918/`
- `records/rebuild_v1_r05_robust_eval_20260918/`
