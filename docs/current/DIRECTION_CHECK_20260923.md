> 历史阶段记录：保留下文当时的判断、建议与条件，不是当前执行指令。研究定位以[研究决策说明](RESEARCH_DECISION.md)为准，待办以[下一步](NEXT_EXPERIMENT.md)为准。特别是外部来源等待、旧seed要求与旧GPU范围不得直接沿用到新任务。

# Research direction check after D9B — 2026-09-23

## Verdict

The scientific problem has stayed aligned with the original goal: robust
Optical/RGB–DSM semantic segmentation when an auxiliary modality is useful,
degraded or absent. The proposed *mechanism* has changed for good reasons.
The original cross-modal high-frequency reliability gate was not a stable
quality estimator (E50), a frequency module alone reduced Potsdam NoBoundary
mIoU at the matched 10k point, and literature already covers generic semantic
prototype reliability, spatial/frequency fusion and availability masking.
The current benefit-aware negative-transfer formulation is therefore a
refinement, not a new application area. See the original archived plan at
`docs/archive/plans/NEXT_EXPERIMENT_PLAN_20260913.md` and the D9 protocol.

| Original commitment | Current evidence and status | Direction decision |
|---|---|---|
| Semantic and frequency cues for modality choice | Handcrafted input-space D9B cues and equal-weight mixtures failed the decision-benefit gate. This is not a test of learned deep semantic prototypes or all frequency designs. | Keep as candidate inputs and explicit ablations, not as ground-truth reliability or the headline claim. |
| Robust complete/local missingness | Known DSM absence has deterministic RGB fallback in the diagnostic router; R05 still fails complete DSM absence relative to R01. | Keep exact fallback as a required capability; learned missingness detection remains unproved. |
| Training-time and inference-time support | B4 teacher distillation failed cross-seed local replication; D9A/D9B used frozen experts only. | A new trained method is still missing. Do not turn a diagnostic score into a method claim. |
| Both RGB and DSM failures | Current rebuild protocol tests only DSM marginal benefit. | DSM-first was a staged scope choice; RGB missing/degradation is still required before any arbitrary-modality claim. |
| Improved segmentation, including small targets | D8 did not pass its prespecified small-Car gate; D9A ranking improvements did not improve routed mean mIoU; D9B combination failed decision ranking. | Make negative-transfer rate, class IoU and mIoU decisive, with Car and Building reported separately. |

The material execution drift is the growing volume of Val2 diagnostics without
a validated new model or independent source. D9B closes the current unfitted
screen. Another reweighting of the same six scores on Val2 would be
post-selection fitting and would not resolve this gap.

## Next phase: source gate, then one method hypothesis

1. **Source gate (no GPU):** Freeze an independent labelled image+height
   semantic-segmentation source, its prior-exposure record, usable scene IDs,
   image bands/GSD, elevation definition, classes and spatially disjoint
   fit/calibration/evaluation partitions. Do not load historical Potsdam Test6.
   If no such source is available, stop the benefit-predictor training line and
   report the current negative evidence; do not substitute repeatedly viewed
   Val2 for a confirmation split.
2. **One new hypothesis after source freeze:** Predict the *decision-relevant
   marginal value* of the dual expert over RGB, with a calibrated abstention
   policy that accepts DSM only when estimated benefit exceeds a prespecified
   risk threshold. Semantic and frequency features remain optional inputs to
   compare against confidence and entropy, not labelled reliability. Preserve
   exact RGB fallback when DSM availability is zero. This is a proposed
   experiment, not an implemented or proven algorithm.
3. **Evaluation gate:** Compare with R01, R05, safe confidence, entropy and a
   label-informed oracle on held-out scenes, both expert seeds, clean and
   global/local missing, blur, downsampling, noise and shift. Report AUROC,
   AUPRC, calibration, selected negative transfer, NoBoundary/FullGT mIoU,
   class and object-size strata. Require both seeds to improve the best simple
   control without severe-noise, Building or missingness regressions before
   training the proposed residual fusion model. RGB failure modes form a
   separate bidirectional extension and are mandatory before claiming
   arbitrary-modality robustness.

## Candidate external source, not yet approved

The [2019 IEEE GRSS DFC US3D description](https://www.grss-ieee.org/community/technical-committees/2019-ieee-grss-data-fusion-contest/)
reports co-registered satellite imagery, LiDAR-derived height and semantic
labels for training regions in two cities. It is a *feasibility candidate*,
not a frozen dataset: available bands/resolution, height-as-input use,
semantic class mapping (especially Car), geographic independence, access and
publication terms must be checked first. Its contest validation/test labels
are not disclosed; only genuinely accessible labelled scenes could form our
own spatially separated evaluation. The official page requires registration
and gives publication-use conditions. No US3D data have been downloaded or
loaded for this decision.
