# D9B: decision-relevant DSM benefit screen

Status (2026-09-23): exploratory unfitted screen completed; the fixed
combination failed its cross-seed entry gate. See
`docs/experiments/D9B_RESULTS_20260923.md`. The design below is the frozen
pre-run protocol, not a plan to repeat the same Val2 scores.

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

## Frozen exploratory implementation (2026-09-23)

The first queue samples the same 200,000 valid NoBoundary pixels per Val2 tile
as D9A for each seed and condition. The primary target is
`dual_only_correct` versus `rgb_only_correct` among argmax disagreements.
It separately counts `both_wrong` and agreement pixels and retains CE-benefit
AUROC/AUPRC with D9A's ±0.01 neutral margin. Class, Train16 component-size
quantiles, damage region and tile are analysis strata only; ground-truth
class and size never enter the score.

The prototype builder uses Train16 tiles only, at most 200,000 uniform valid
pixels per tile and 5,000 per class per tile. Fixed *input-space* RGB features
are three optical channels and centered grayscale edge magnitudes at radii
2 and 8 pixels. DSM features are normalized height and centered edge
magnitudes at the same radii. Class-conditional Gaussian means and standard
deviations yield `exp(-0.5 * mean(standardized squared distance))`.
This is a handcrafted multiscale class-prototype **control**, not a faithful
replication of SGMA's learned deep-feature prototypes. Frequency evidence is
mean unsigned RGB–DSM edge alignment at radii 2 and 8, mapped to [-1, 1].
It is an image-quality cue, not a true-reliability measurement. Class
prototype lookups use each expert's *predicted* class.

Six score orientations are frozen in `scripts/d9b_observable_features.py`
(larger favors R05): dual-minus-RGB maximum confidence; RGB-minus-dual
predictive entropy; `0.5 * (dual RGB prototype + dual DSM prototype) - RGB
prototype`; edge alignment; equal-weight semantic and frequency; and the
mean of semantic, frequency, normalized entropy margin and signed
Jensen–Shannon disagreement. No weights or thresholds are fitted. Compare
AUROC/AUPRC to the stronger of confidence and entropy per seed-condition,
then to semantic-only. D9A already provides confidence and entropy routing
mIoU controls.

This queue does not calibrate probabilities, compute ECE, optimize thresholds
or route a composite score. Its ranking metrics are diagnostic, not mIoU or
negative-transfer gains. Any later routing experiment needs independent
labelled scenes and a new frozen protocol. Hard DSM absence must still force
deterministic RGB fallback.

## Decision

Advance a combination only if it improves both seeds over the strongest
confidence, entropy and semantic-only controls on decision-relevant benefit
ranking and does not worsen Building or severe DSM-noise routed mIoU. The
original full-D9 entry gate in `docs/protocols/D9_DSM_BENEFIT_DIAGNOSTIC.md`
still applies; this screen cannot waive it. If the contrast is weak or
seed-dependent, do not train the proposed residual gate.
