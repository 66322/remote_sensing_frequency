# Experiment Report: C-OO-QD Matched Capacity and Augmentation Control

## Basic information

- experiment ID: C-OO-QD
- status: complete
- started at: 2026-09-18T11:16:57+08:00
- completed at: 2026-09-18T17:16:05+08:00
- source Git commit: 1f858b97fa8ada4f1e4321bdd8d6da35fb07ce3c
- seed: 42
- schedule: 16000 optimizer steps
- best step: 15000
- historical TEST6 loaded: false

## Purpose

Provide a second-stream capacity and Q+D augmentation control for R05 without
using DSM values. The second branch receives fixed Optical grayscale.

## Main clean result

| Metric | Result |
|---|---:|
| FullGT mIoU_fg5 | 81.6670 |
| NoBoundary mIoU_fg5 | 86.1969 |
| R05 minus C-OO-QD FullGT | +0.8477 pp |
| R05 minus C-OO-QD NoBoundary | +0.8516 pp |

## Matched second-stream degradation comparison

| Condition | R05 NB | C-OO-QD NB | R05 minus control |
|---|---:|---:|---:|
| clean | 87.0486 | 86.1968 | +0.8517 pp |
| branch-2 blur5 | 86.8219 | 85.4216 | +1.4003 pp |
| branch-2 down2 | 86.8970 | 85.8434 | +1.0536 pp |
| branch-2 down4 | 86.4557 | 83.8099 | +2.6458 pp |
| branch-2 down8 | 85.5023 | 79.3520 | +6.1502 pp |
| branch-2 zero | 83.1294 | 84.5740 | -1.4446 pp |

## Conclusion

R05 has a positive advantage over the matched control under clean and degraded
second-stream conditions, especially down8. This supports condition-dependent
DSM value beyond a simple second-stream capacity explanation.

Under complete second-stream removal, R05 is worse than C-OO-QD and remains
below R01. The system therefore still has a fallback-dependence problem.

Optical-zero results are not treated as a direct matched DSM-value comparison,
because the control's second branch also contains Optical information.

## Limitations

Single seed and two validation tiles. D1-D3 local diagnostics are required
before making spatial-reliability claims.

## Artifacts

- `configs/rebuild_v1/c_oo_qd_optical_gray_16k.json`
- `records/rebuild_v1_c_oo_qd_formal_16k_20260918/`
- `records/rebuild_v1_c_oo_qd_robust_eval_20260918/`
