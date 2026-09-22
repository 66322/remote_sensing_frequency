# Next experiment decision after B4

- Status: D7 diagnostic queue prepared; no new model training approved
- Last completed gate: B4 seed17 replication
- Decision: current SafeMaxConfidence distillation route is closed as the proposed
  main method because the documented local replication criteria failed
- Device rule for any future run: physical GPU0 only
- Persistent scope: `/home/jovyan/zzx`

## What B4 resolved

KD17 remains slightly above R05_KD17 under global down8 (+0.2093 pp) and DSM-zero
(+0.0438 pp), but it is worse in both paired local damaged-region families. It is
also 0.1202 pp below matched CE continuation on global DSM-zero. The result supports
a small global trend, not a replicated local reliability mechanism or a generally
better robust model.

## Work that must not be queued

- another identical C/R05_KD/KD run on seed42 or seed17;
- a longer continuation budget for the unchanged models;
- another SAFE or AVG_KD run without a new causal question;
- claims or experiments that treat known zero-fill masks as learned missing-data
  detection;
- final model selection on the repeatedly inspected two-tile Val2 split.

## Required next design gate

Before new training, write and review a protocol that separates three mechanisms:

1. **Known-mask supervision:** R01 inside the synthetic missing mask and fixed R05
   elsewhere, without confidence selection.
2. **Confidence selection:** teacher selection without access to the synthetic
   missing mask, with teacher confidence calibration checked first.
3. **Deployable fallback:** an explicit Optical anchor or quality estimator whose
   inference inputs are actually available under real missing/degraded DSM.

The protocol must include a new frozen evaluation source, preferably a second
dataset or previously untouched tiles. It must define a matched CE baseline,
ordinary R05-teacher KD, mask-only teacher, confidence-only teacher and the proposed
method. The primary unit must be tiles/scenes rather than pixels or quadrants.

## Decision rule for resuming GPU work

Queue a new run only after the method differs materially from B1–B4, all controls
are specified, the evaluation data are frozen, and success thresholds are written
before results are viewed. Until then, the correct next action is paper/evidence
consolidation and protocol design, not another training queue.

## Immediate diagnostic: D7

D7 audits Train16 class/crop exposure and existing R01/R05 seed42/17 errors by
class, connected-object size and true semantic boundary under clean, DSM down8 and
DSM zero. It performs no training and does not reopen the closed B1–B4 method.

Protocol: `docs/protocols/D7_DATA_SCALE_BOUNDARY_AUDIT.md`.

Only after D7 is summarized may one small R01 training screen be specified. The
screen must isolate sampling from loss design and retain a matched CE control. D7
Val2 flags alone cannot support paper claims or replace a new frozen evaluation
source.
