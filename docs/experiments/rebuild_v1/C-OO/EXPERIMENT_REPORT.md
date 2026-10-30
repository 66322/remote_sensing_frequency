# Experiment Report: C-OO Optical+Optical Capacity Control

## Basic information

- experiment ID: C-OO
- status: complete
- started at: 2026-09-17T20:29:11+08:00
- completed at: 2026-09-18T02:26:26+08:00
- time source: overnight queue log
- seed: 42
- schedule: 16000 optimizer steps
- best step: 13000
- historical TEST6 loaded: false

## Purpose

Test whether the clean R02 improvement over true Optical-only R01 is caused by
DSM information or can be explained by a second-stream capacity and
architecture effect.

## Control

The second branch receives fixed Optical grayscale rather than DSM. The
dual-stream structure and training budget are matched to the clean dual model.

## Main result

| Metric | Result |
|---|---:|
| FullGT mIoU_fg5 | 81.8281 |
| NoBoundary mIoU_fg5 | 86.3548 |
| R02 NoBoundary mIoU_fg5 | 86.2016 |
| C-OO minus R02 | +0.1532 pp |

## Conclusion

C-OO slightly exceeds R02 on the two-tile Val2 development split. Therefore,
the full R02-R01 clean improvement cannot be attributed to DSM-specific
information.

This does not prove that DSM has no value under every condition. It shows that
a capacity-matched second-stream control is mandatory.

## Limitations

Single seed and two validation tiles. The Optical grayscale second branch is a
capacity control, not a semantically identical replacement for DSM.

## Artifacts

- `configs/rebuild_v1/c_oo_optical_optical_capacity_16k.json`
- `scripts/train_rebuild_v1_c_oo_capacity.py`
- `records/rebuild_v1_c_oo_formal_16k_20260918/`
