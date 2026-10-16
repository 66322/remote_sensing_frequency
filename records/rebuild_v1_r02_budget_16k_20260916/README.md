# REBUILD_V1 R02 complete-schedule budget pilot — 16k

Date: 2026-09-16
Timezone: UTC+08:00

## Purpose

Test whether extending the complete learning-rate decay horizon from 12k to 16k removes the endpoint-improvement ambiguity observed in the completed 12k pilot, before freezing one common schedule for formal R01-R04 comparisons.

This is a development/budget-selection run on REBUILD_V1 Train16/Val2. Historical Potsdam TEST6 was not loaded.

## Protocol

- model: R02 clean dual-modal F0 baseline
- seed: 42
- Train16 / Val2 split: `configs/rebuild_v1/potsdam_split_seed20260915.json`
- patch: 512
- micro batch: 4
- accumulation: 4
- effective batch: 16
- optimizer: AdamW
- backbone LR: 6e-5
- decoder/head LR multiplier: 10x
- warmup: 1200 steps
- complete scheduler horizon: 16000 steps
- stop step: 16000
- validation interval: 1000 steps
- validation selection metric: Val2 NoBoundary mIoU_fg5
- validation stride: 256
- TEST6 loaded: false

The 16k run was fresh-from-initialization/pretrained weights. It did not resume the completed 12k schedule.

## Timing

- started_at: approximately `2026-09-16T11:19+08:00` (minute precision from retained process start display)
- completed_at: exact clock time not retained in the committed training artifact
- confirmed_complete_by: `2026-09-16T17:32+08:00` from the post-run server inspection that showed the process defunct and the log ending with `COMPLETE`

Do not infer a more precise completion time from optimizer-step duration.

## Validation trajectory

| Step | FullGT mIoU_fg5 (%) | NoBoundary mIoU_fg5 (%) |
|---:|---:|---:|
| 1000 | 70.7962 | 74.9748 |
| 2000 | 74.0176 | 78.2016 |
| 3000 | 75.4704 | 79.4686 |
| 4000 | 78.1339 | 82.5652 |
| 5000 | 79.6730 | 84.2419 |
| 6000 | 75.8007 | 79.8514 |
| 7000 | 79.5687 | 84.0377 |
| 8000 | 79.7589 | 84.4742 |
| 9000 | 81.0382 | 85.3623 |
| 10000 | 80.3745 | 84.7059 |
| 11000 | 80.6975 | 84.8247 |
| 12000 | 80.9853 | 85.0438 |
| 13000 | **81.8483** | **86.2016** |
| 14000 | 81.8172 | 86.1183 |
| 15000 | 81.3686 | 85.6580 |
| 16000 | 81.6683 | 86.0244 |

Best checkpoint by the frozen selection metric:

- step: **13000**
- Val2 NoBoundary mIoU_fg5: **86.2016%**
- corresponding FullGT mIoU_fg5: **81.8483%**

Final step 16000:

- FullGT OA: 88.8809%
- FullGT mIoU_fg5: 81.6683%
- NoBoundary OA: 91.0310%
- NoBoundary mIoU_fg5: 86.0244%

## Budget decision

**Freeze the complete schedule at 16k for formal R01-R04.**

Reasoning:

1. The 12k complete schedule ended with its best validation score at the schedule endpoint, leaving an endpoint-improvement ambiguity.
2. In the fresh 16k schedule, the best Val2 NoBoundary score occurs at 13k rather than at the endpoint.
3. The late 13k-16k region does not show sustained endpoint improvement: 86.2016 -> 86.1183 -> 85.6580 -> 86.0244.
4. Extending to another schedule is therefore not justified by the predeclared decision rule.
5. Formal runs should use the same complete 16k schedule and select checkpoints using Val2 only.

## Important schedule-comparison note

At step 12000, the fresh 16k schedule reaches 85.0438% NoBoundary mIoU_fg5, while the separate complete 12k schedule reached 85.4135% at its own step 12000. This is expected because the LR trajectories differ. It reinforces the rule that the first N steps of a longer schedule are not equivalent to a complete N-step schedule.

## Next step

Proceed to the formal matched matrix:

1. R01: genuine Optical-only baseline;
2. R02: matched clean Optical+DSM baseline;
3. R03: matched dual model with quality-corruption training Q;
4. R04: matched dual model with modality dropout D.

The first causal gate remains matched Fusion Gain under clean and DSM-degraded conditions; do not claim harmful fusion before R01 exists.
