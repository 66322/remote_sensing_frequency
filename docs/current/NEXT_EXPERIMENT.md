# Next experiment decision after D8

- Updated: 2026-09-23
- Current gate: D8 seed42 fixed-step C/A/S sampling screen completed; both A
  and S failed the predeclared conjunctive gate.
- Decision: do not launch D8 seed17 or change the D8 thresholds post hoc.
- Device and persistence: physical GPU 0 only; all runtime outputs under
  `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro`.
- Historical TEST6 remains frozen.

## Next action: D9 benefit diagnostic

Use the existing R01 RGB expert and R05 RGB+DSM expert at seeds 42 and 17 to
measure the label-defined pixel benefit of adding DSM:

`benefit = CE(R01, y) - CE(R05, y)`.

Compare confidence, entropy, SGMA-style semantic prototype similarity,
frequency/image-quality features, semantic+frequency features, and the same
features plus expert disagreement. Include D5 SafeMaxConfidence and a label-
informed oracle as controls. Report benefit and harm AUROC/AUPRC, calibration,
negative-transfer rate and mIoU by class, size, corruption, tile and seed.
Protocol: `docs/protocols/D9_DSM_BENEFIT_DIAGNOSTIC.md`.

The immediate runnable step is the D9A read-only frozen-expert inference
and direct-score audit on Val2 (`scripts/run_rebuild_v1_d9a_queue_20260923.sh`).
A fitted combination and any safety-gate training
require a previously frozen, spatially independent fitting/calibration/evaluation
source. Val2 alone supports only exploratory ranking. Freeze numeric success
thresholds before fitting the combinations. Do not load TEST6 for D9.

The new method is eligible for training only if combined evidence shows a
consistent benefit-prediction and negative-transfer advantage over confidence
and semantic-only controls in both seeds. The candidate residual form is

`Zsafe = ZRGB + availability_DSM * gate * (Zdual - ZRGB)`.

With `availability_DSM=0`, output must exactly equal `ZRGB`. RGB-missing
robustness belongs to a later bidirectional protocol; it is not established by
the first D9 stage.
