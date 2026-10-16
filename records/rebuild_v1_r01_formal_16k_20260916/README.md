# REBUILD_V1 R01 true Optical-only formal 16k

Date: 2026-09-16
Timezone: UTC+08:00
Branch execution commit: `3e5cff755316d4c14b170a60a012c26555c9fbbf`

## Purpose

Establish a genuine Optical-only baseline under the frozen REBUILD_V1 16k protocol, with the DSM branch completely absent, so that matched clean Fusion Gain and compute overhead can be measured against R02.

## Structural validity

The run used the dedicated true Optical-only model rather than feeding zeros through the dual-modal model.

- model forward inputs: 1
- forbidden DSM/depth parameter names: none
- structural audit: PASS
- DSM loaded: false
- historical TEST6 loaded: false
- total/trainable parameters: 105,950,198

## Timing

- started_at: `2026-09-16T18:39:18+08:00`
- completed_at: `2026-09-16T22:51:38+08:00`
- queue stage A2 completed_at: `2026-09-16T22:51:39+08:00`

## Frozen protocol

- seed: 42
- Train16 / Val2 split
- patch: 512
- effective batch: 16
- complete scheduler horizon: 16000 optimizer steps
- warmup: 1200 steps
- validation interval: 1000 steps
- selection metric: Val2 NoBoundary mIoU_fg5
- TEST6: excluded

## Validation trajectory

| Step | FullGT mIoU_fg5 (%) | NoBoundary mIoU_fg5 (%) |
|---:|---:|---:|
| 1000 | 69.6803 | 74.1885 |
| 2000 | 74.0397 | 78.3796 |
| 3000 | 75.8495 | 80.2013 |
| 4000 | 77.6512 | 81.9673 |
| 5000 | 78.1179 | 82.6437 |
| 6000 | 78.2321 | 82.4608 |
| 7000 | 79.2460 | 84.2263 |
| 8000 | 77.6508 | 82.2490 |
| 9000 | 77.6756 | 82.3925 |
| 10000 | **80.6883** | **85.3713** |
| 11000 | 80.2207 | 84.6172 |
| 12000 | 79.8634 | 84.3295 |
| 13000 | 79.6453 | 83.8697 |
| 14000 | 80.6764 | 85.0707 |
| 15000 | 80.0051 | 84.4291 |
| 16000 | 80.5163 | 84.9760 |

Best checkpoint by the frozen selection metric:

- step: **10000**
- Val2 NoBoundary mIoU_fg5: **85.3713%**
- corresponding FullGT mIoU_fg5: **80.6883%**

Final step 16000:

- FullGT OA: 87.4774%
- FullGT mIoU_fg5: 80.5163%
- NoBoundary OA: 89.6387%
- NoBoundary mIoU_fg5: 84.9760%

## Immediate matched clean comparison to canonical R02

Canonical R02 best checkpoint:

- step: 13000
- NoBoundary mIoU_fg5: 86.2016%
- FullGT mIoU_fg5: 81.8483%

Approximate clean matched gains using each model's Val2-selected checkpoint:

- NoBoundary: `86.2016 - 85.3713 = +0.8303 pp`
- FullGT: `81.8483 - 80.6883 = +1.1600 pp`

Interpretation: the clean dual-modal system is better than the matched true Optical-only baseline on Val2, but the gain is modest. These differences represent the total gain of the matched dual-modal design over its single-stream counterpart; they should not yet be attributed purely to DSM information because R02 also contains additional dual-stream capacity and multimodal interaction.

A dual-capacity control such as Optical+Optical may be added later if the distinction between extra architecture capacity and DSM-specific information becomes important.

## Queue progression observed after R01

- A3 R01 profile: complete at `2026-09-16T22:52:04+08:00`
- A4 R01/R02 Fusion-Gain severity: complete at `2026-09-16T22:55:06+08:00`
- R04 smoke: complete at `2026-09-16T22:58:24+08:00`
- R04 formal 16k: complete at `2026-09-17T04:54:42+08:00`
- R04 evaluation: complete at `2026-09-17T04:58:45+08:00`
- R03 smoke: complete at `2026-09-17T05:02:06+08:00`
- R03 formal 16k: running as of the latest server inspection.

Do not infer A4/R04 scientific outcomes from stage completion alone; archive their result files after the queue reaches the next safe inspection point.
