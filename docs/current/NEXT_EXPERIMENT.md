# Next decision after D9B — 2026-09-23

D9B completed with zero user-reported queue failures. The fixed
semantic+frequency+expert score beat the better confidence/entropy control
in only 1/16 flip-benefit AUROC and 0/16 AUPRC comparisons. The exact Val2
screen is closed; it does not authorize a safety-gate fit. The full result
and evidence boundary are in `docs/experiments/D9B_RESULTS_20260923.md`.

The original research goal remains robust RGB–DSM semantic segmentation
under modality degradation and absence. The method claim has narrowed from
generic semantic/frequency reliability to **predicting DSM's marginal
decision benefit and suppressing negative transfer**. The comparison with
the original plan, including unfinished RGB-missing and training/inference
requirements, is in `docs/current/DIRECTION_CHECK_20260923.md`.

## Immediate next action: independent source decision

Before any new GPU experiment, identify an additional labelled image+height
segmentation scene set that has not been used for method selection. Freeze:

1. exact available scene IDs, geographic relation and previous exposure;
2. optical bands, DSM/nDSM meaning, spatial resolution and alignment;
3. semantic classes and whether Car/Building analyses remain possible;
4. spatially disjoint fit, calibration and evaluation scenes;
5. data access and publication conditions.

Only metadata are needed for this decision. Do not load historical Potsdam
Test6. Known Potsdam Train16 and repeatedly inspected Val2 are ineligible as
independent confirmation; earlier Vaihingen train12/test4 were also exposed.
US3D is a conditional candidate, not yet approved. See
`docs/current/D9B_SOURCE_STATUS_20260923.md` and the source note in the
direction check.

If an eligible source is frozen, write a new protocol for **one** fitted
benefit predictor with calibrated abstention, exact DSM-absence RGB fallback,
and matched confidence/entropy/semantic/frequency controls. The fit and
calibration splits cannot overlap the final evaluation scenes. Apply the
entry gate in `docs/protocols/D9_DSM_BENEFIT_DIAGNOSTIC.md` before training
residual fusion. Include DSM complete/local absence, blur, downsampling,
noise and misalignment; the bidirectional RGB-failure extension remains
required before claiming arbitrary-modality support.

If no source qualifies, stop this benefit-predictor training line and write
up the D9A/D9B negative evidence. Do not optimize the same six scores on
Val2 or relaunch B1–B4, D8 or D9A.

Every future run uses physical GPU 0, writes only under `/home/jovyan/zzx`,
continues the queue after individual failures, and keeps Test6 frozen.
