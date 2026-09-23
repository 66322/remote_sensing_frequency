# D9B: decision-relevant DSM benefit screen

## Question

D9A is closed. Entropy difference improved cross-entropy benefit ranking in
all 16 conditions but did not improve routed mIoU, while Car and Building IoU
moved in opposite directions. D9B asks whether observable semantic, frequency
and expert evidence predicts **when choosing the dual expert changes the
segmentation decision beneficially**, rather than merely shifting the true
class probability. This is the next substantive experiment, not another D9A
log audit.

## Frozen target and controls

Use the same frozen seed42/17 R01 RGB and R05 RGB+DSM experts. For each valid
NoBoundary pixel, record both the continuous CE benefit and the two predicted
classes. On pixels where expert argmax predictions differ, classify:

- `dual_only_correct`: R05 is correct and R01 is wrong;
- `rgb_only_correct`: R01 is correct and R05 is wrong;
- `both_wrong`: neither predicts the true class.

Keep the `both_wrong` group visible rather than silently discarding it. Expert
agreement pixels have zero routing effect on the predicted label and must be
reported separately from disagreement pixels. Include correctness-flip AUROC
and AUPRC, all-pixel CE-benefit ranking, routed NB mIoU and class IoU, and
selection/harm counts. Report Car, Building, predicted component-size strata,
tile, seed and each clean/degraded/local condition. Class and size features
available only from ground truth may be used for *analysis*, never as router
inputs.
Under known complete or local DSM absence, availability overrides every
score and forces RGB; any oracle advantage of R05 there is diagnostic only,
not a deployable selection target.

Compare confidence difference, entropy difference, SGMA-style semantic
prototype similarity, observable RGB/DSM frequency or image-quality features,
semantic+frequency, and semantic+frequency+expert disagreement. Prototypes
must be formed from training data only. Fix feature definitions and any
normalization before viewing D9B scores. Do not call prototype similarity,
frequency energy or attention a ground-truth reliability estimate. The
confidence and entropy routes from D9A remain decision baselines.

The first D9B screen may be exploratory on Val2 with **unfitted scores only**;
it cannot establish a new method or generalization claim. Any fitted
combination, calibration, threshold or safety-residual gate requires a
separately frozen, spatially disjoint labelled source. The known Potsdam
Train16/Val2/Test6 and historical Vaihingen train12/test4 scenes are already
exposed. Historical Test6 must not be loaded. If no new eligible source is
available, stop at an exploratory screen and report the limitation.

## Decision

Advance a combination only if it improves both seeds over the strongest
confidence, entropy and semantic-only controls on decision-relevant benefit
ranking and does not worsen Building or severe DSM-noise routed mIoU. The
original full-D9 entry gate in `docs/protocols/D9_DSM_BENEFIT_DIAGNOSTIC.md`
still applies; this screen cannot waive it. If the contrast is weak or
seed-dependent, do not train the proposed residual gate.
