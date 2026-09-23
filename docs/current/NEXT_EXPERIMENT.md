# Next experiment decision after D9A

- Updated: 2026-09-23
- Current gate: D9A frozen-expert direct-score audit completed on both seeds
  and eight conditions with no queue failures.
- Correction: original D9A forced RGB in local down8, affecting only that
  condition's D5 routed mIoU and selected harm. The two-stage fix1 queue
  completed with zero failures and preserved ranking CSVs byte-for-byte.
- Decision: confidence×JS disagreement does not improve benefit ranking over
  confidence difference in any of the 16 comparisons. Do not fit a safety
  gate from this result. D8 seed17 also remains closed.
- Device and persistence: physical GPU 0 only; all runtime outputs under
  `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro`.
- Historical TEST6 remains frozen.

## Next action: D9A entropy decision audit, then D9B source decision

Use the existing R01 RGB expert and R05 RGB+DSM expert at seeds 42 and 17 to
measure the label-defined pixel benefit of adding DSM:

`benefit = CE(R01, y) - CE(R05, y)`.

Compare confidence, entropy, SGMA-style semantic prototype similarity,
frequency/image-quality features, semantic+frequency features, and the same
features plus expert disagreement. Include D5 SafeMaxConfidence and a label-
informed oracle as controls. Report benefit and harm AUROC/AUPRC, calibration,
negative-transfer rate and mIoU by class, size, corruption, tile and seed.
Protocol: `docs/protocols/D9_DSM_BENEFIT_DIAGNOSTIC.md`.

D9A is complete. A read-only review finds entropy difference above confidence
difference on AUROC and AUPRC in all 16 seed-by-condition comparisons.
The entropy stratum audit is complete: Car wins 16/16 AUROC/AUPRC comparisons,
small Car wins 16/16 AUROC and 15/16 AUPRC, and damaged regions win 4/4 on
both metrics. The local-down8 correction is complete: D5 NB mIoU is
86.8285%/86.2557% at seeds 42/17. The other 14 D9A conditions must not be
repeated.

The old D5 per-seed result directories are absent under project `records/`,
although its seed42/17 logs report `D5 COMPLETE`. Its queue status file is
also absent. A new, predeclared D9A entropy-routing decision audit is running
at `docs/protocols/D9A_ENTROPY_ROUTING_DECISION_AUDIT.md`. It measures routed
mIoU and selected harm for safe entropy versus corrected safe confidence on
the same eight conditions and both seeds. It is exploratory Val2 analysis,
uses only frozen experts, and cannot establish a new method claim. The queue
started at 2026-09-23 13:00:35 +08:00; smoke passed and seed42 clean started.
Wait for its independent failure-continue stages, then validate the
source-hashed summary against the existing D9A expert and confidence outputs.

After the route audit, perform a read-only D9B source audit. Inventory RGB/DSM
images, labels, scene IDs and prior experiment exposure for a second dataset
or genuinely untouched scenes. Earlier Vaihingen work already used train tiles
`1,3,7,11,13,17,23,26,28,32,34,37` and evaluated on `5,15,21,30`;
neither documented set is an untouched final test. See
`docs/current/D9B_SOURCE_STATUS_20260923.md`. Freeze spatially disjoint
fitting, calibration and evaluation scenes and the condition generator before
extracting fitted features. If no independent labelled source exists, keep
D9B as a protocol and report D9A as exploratory rather than fitting on Val2.
R01/R05 were trained on Train16, Val2 has been repeatedly inspected, and
historical TEST6 is frozen. Do not start a learned-router queue on Val2.

Only after a source is frozen, compute the D9 comparison ladder on the same
pixels: confidence, entropy, SGMA-style semantic prototypes, observable
frequency/image quality, semantic+frequency, and the same features plus
expert disagreement. Use identical conditions and class/size/region strata,
fit/calibrate only on designated scenes, and compare to the strongest direct
control from the entropy-route audit. Apply the entry gate in
`docs/protocols/D9_DSM_BENEFIT_DIAGNOSTIC.md` before training a residual gate.

The new method is eligible for training only if combined evidence shows a
consistent benefit-prediction and negative-transfer advantage over confidence
and semantic-only controls in both seeds. The candidate residual form is

`Zsafe = ZRGB + availability_DSM * gate * (Zdual - ZRGB)`.

With `availability_DSM=0`, output must exactly equal `ZRGB`. RGB-missing
robustness belongs to a later bidirectional protocol; it is not established by
the first D9 stage.
