# Next experiment decision after D9A

- Updated: 2026-09-23
- Current gate: D9A frozen-expert direct-score audit completed on both seeds
  and eight conditions with no queue failures.
- Correction: original D9A forced RGB in local down8, affecting only that
  condition's D5 routed mIoU and selected harm. Correct those two stages.
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
both metrics. First run `scripts/run_rebuild_v1_d9a_local_down8_fix1_20260923.sh`
and validate with `scripts/summarize_rebuild_v1_d9a_local_down8_fix1.py`.
These correct only two affected existing-model evaluations; the other 14
D9A conditions must not be repeated.

The expected old D5 `method_metrics.csv` paths are missing. Locate any
existing D5 original metrics within the project records and
archive them. If genuinely absent, specify one narrow frozen-expert routing
evaluation that measures entropy-route mIoU and selected harm; this is a new
decision diagnostic, not a repetition of the D9A ranking screen. See
`docs/experiments/D9A_RESULTS_20260923.md`.

After that, decide whether D9B has a concrete, independent source for
fitting/calibration/evaluation. R01/R05 were trained on Train16, Val2 has been
repeatedly inspected, and historical TEST6 is frozen. Therefore a fitted
semantic/frequency combination cannot claim an unbiased test on the current
Potsdam split. Do not start a model-training or learned-router queue on Val2.

The new method is eligible for training only if combined evidence shows a
consistent benefit-prediction and negative-transfer advantage over confidence
and semantic-only controls in both seeds. The candidate residual form is

`Zsafe = ZRGB + availability_DSM * gate * (Zdual - ZRGB)`.

With `availability_DSM=0`, output must exactly equal `ZRGB`. RGB-missing
robustness belongs to a later bidirectional protocol; it is not established by
the first D9 stage.
