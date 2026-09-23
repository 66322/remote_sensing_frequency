# Completed, Closed, or Do-Not-Repeat Work

Before launching work, compare the proposed experiment with this file and
`records/rebuild_v1_experiment_registry.json`.

Follow-up completion is user-reported; original large artifacts remain on the server.
Missing GitHub evidence is a reason to archive outputs, not rerun experiments.
B1–B4 are complete. No duplicate B4 queue or unchanged follow-up is justified.

## Closed historical directions

| Direction | Decision |
|---|---|
| Decoder-side frequency stacking | Only limited gain; no longer the main line. |
| Crop 256 | Did not provide the required advantage; stopped. |
| History30 sampling | Did not outperform Rare30; stopped. |
| Rare15 plus History15 | Did not improve the retained baseline; stopped. |
| Normal shallow detail | Final result below the retained baseline; stopped. |
| HF shallow detail | Final result below the retained baseline with class redistribution; stopped. |
| Legacy E50 reliability gate | Gate response was not a stable degradation estimator; motivation only. |
| E51 fixed-grid factor expansion | Did not support a PH-specific robustness advantage; closed. |
| Test-time GSD injection | Negative result; do not revive without a new causal design. |

## Completed REBUILD_V1 work

Do not rerun the same dataset, split, seed, schedule and configuration:

- R01 Optical-only seed42 16k;
- R02 clean Optical+DSM seed42 12k development pilot;
- R02 clean Optical+DSM seed42 16k canonical baseline;
- R03 quality-corruption seed42 16k;
- R04 modality-dropout seed42 16k;
- R01-R04 core robustness matrix;
- C-OO Optical+Optical capacity control seed42 16k;
- R05 Optical+DSM Q+D seed42 16k;
- C-OO-QD matched capacity/augmentation control seed42 16k;
- matched global robustness evaluation for R05 and C-OO-QD.
- D1-D3 local missing, local down8 and spatial-shift diagnostics for R05 and
  C-OO-QD;
- A1 no-Optical-dropout seed42 16k;
- A2 20%-DSM-dropout/no-Optical-dropout seed42 16k;
- R01, R05 and C-OO-QD seed17 16k replications and matched robustness checks.
- D4 frozen-expert complementarity analysis for seeds 42 and 17;
- D5 probability/confidence routing for seeds 42 and 17;
- D6 variable-shape missing/degraded-mask generalization for SafeMaxConfidence.
- B1 seed42 matched CE/KD/SAFE 4k continuation and robust evaluation;
- B2 seed42 R05-teacher and average-teacher controls;
- B3 seed42 paired damaged/boundary regional diagnostics for C, KD, SAFE,
  R05_KD and AVG_KD.
- B4 seed17 matched C/R05_KD/KD 4k continuation, global robustness and paired
  local damaged-region replication.
- D7 Train16 sampling and seed42/17 semantic-error audit;
- D8 seed42 4000-step C/A/S crop-sampling screen and `fix1` summary.
- D9A seed42/17 frozen-expert direct-score benefit audit across eight DSM
  conditions; do not rerun identical inference.

## Important negative or limiting findings

- R02 12k is not the formal budget; the accepted complete schedule is 16k.
- R03 is strong for mild/moderate quality degradation but does not solve
  complete DSM absence.
- R04 repairs much of the DSM-zero failure but remains below true R01.
- R05 still remains below R01 when DSM is completely absent.
- C-OO clean outperforming R02 means clean dual-stream improvement alone is
  not proof of DSM-specific value.
- Optical-zero comparisons between R05 and C-OO-QD are not semantically matched.
- A1 worsens DSM-zero fallback despite retaining 10% DSM dropout.
- A2 improves DSM-zero over R05 seed42 but remains 1.4421 pp below R01 and
  loses 1.2549 pp clean performance relative to R05 seed42.
- Increasing modality-dropout probability alone is not the active route.
- Spatial shifts produce monotonic but modest loss; do not add a registration
  module before a safer fusion path has been demonstrated.
- D4 rejects a degradation-only frozen-expert gate: local down8 prefers R05 at
  seed42 but R01 at seed17. Do not treat DSM quality as expert benefit.
- D5 SafeMaxConfidence passes the shared seed42/seed17 clean, DSM-zero and
  DSM-down8 gate; fixed probability mixtures and unconstrained confidence or
  entropy routing do not pass both seeds.
- D6 explicit/inferred-zero scores agree to four printed decimals but are not
  exactly equal in all supplied raw rows; no mask-equality test was performed.
  Known zero-fill detection is not evidence of real missing-data detection.
- D5 only supplies hard missing-region fallback to maximum-confidence routing.
  Safe probability-average/entropy controls remain untested, not ruled out.
- D4's rejected "B1 frozen-expert gate" proposal is NOT the current B1
  single-student distillation pilot; preserve this distinction in handoffs.
- B1 SAFE does not consistently improve on KD; do not repeat it unchanged.
- B2 AVG_KD does not consistently improve on KD; do not repeat it unchanged.
- B3 supports KD over R05_KD within seed42, but local missing boundaries remain
  mixed against CE.
- B4 repeats the small KD-over-R05_KD global down8/zero direction but reverses both
  paired local damaged-region directions. The documented B4 decision gate fails.
- KD17 is 0.1202 pp below C17 on global DSM-zero. Do not claim the current KD is a
  generally superior robust model.
- Do not repeat or extend the unchanged SafeMaxConfidence distillation route. A new
  run requires a materially changed reliability design and a new frozen evaluation
  source.
- D8-S improves small-Car indicators but fails the prespecified +2 pp mean
  correctness and +3 pp recall@50 joint gate. D8-A also fails. Do not run the
  conditional D8 seed17 replication or relax the gate after seeing Val2.
- Semantic prototype similarity, frequency quality, confidence and availability
  are candidate D9 evidence or controls. Do not relabel them as ground-truth
  reliability or claim them alone as the main innovation.
- D9A confidence-difference times Jensen-Shannon disagreement loses to direct
  confidence difference on benefit AUROC and AUPRC in all 16 reported
  seed-by-condition comparisons. Do not present this interaction as the new
  mechanism or retrain it unchanged on Val2.
- D9A entropy difference beats confidence difference on CE-benefit AUROC and
  AUPRC in all 16 comparisons. This is an existing baseline, not a novel gate;
  do not equate ranking with routed mIoU or a calibrated benefit probability.
- The matched safe-entropy routing audit completed with zero failures. It won
  NB mIoU over safe confidence in only 4/16 seed-condition rows, lost in 10,
  and tied in both DSM-zero rows. Do not repeat it or claim simple lower-entropy
  routing as a safety improvement.
- Original D9A `dsm_local_down8_q1` D5 routing masked degraded DSM as if it
  were absent. Its two original D5 mIoU and selected-harm rows are invalid;
  the documented two-seed `fix1` correction is complete. Do not rerun it.

## Legitimate reasons to rerun

A rerun requires at least one explicitly documented new variable:

- a new random seed for variance estimation;
- a new dataset;
- a new frozen split;
- a corrected implementation with a documented defect;
- a new training budget justified by convergence evidence;
- a new model component;
- a new corruption or diagnostic protocol.

A new filename or experiment ID alone is not a valid reason.
