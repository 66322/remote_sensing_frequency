# Completed, Closed, or Do-Not-Repeat Work

Before launching work, compare the proposed experiment with this file and
`records/rebuild_v1_experiment_registry.json`.

Follow-up completion is user-reported; original artifacts await archival.
Missing GitHub evidence is a reason to archive outputs, not rerun experiments.
B1 is running as last reported; do not start a duplicate queue.

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
