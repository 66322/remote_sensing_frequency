# D9: predict the marginal benefit of DSM before training a safety gate

## Research question and boundary

Can inference-time evidence predict where an existing dual expert improves or
harms an existing RGB expert? D9 is a frozen-expert diagnostic, not a new model
training queue. It uses the existing R01 (true RGB-only) and R05 (RGB+DSM Q+D)
seed42/17 checkpoints. Historical TEST6 remains frozen and must not be loaded.
Val2 findings are development evidence only. Any paper-level method claim later
requires a newly frozen evaluation source that was not used for method selection.

The proposed contribution is benefit-aware suppression of negative transfer.
Semantic prototype similarity, frequency energy, confidence and modality
availability are candidate inputs or controls, not ground-truth reliability or
standalone innovations. STARS, SGMA, PE-MMRSS, CAF-Net and CBC-SLP already cover
substantial parts of shared/specific representations, semantic prototypes,
quality-aware fusion, frequency features and missing-modality support.

## Target, prediction unit and leakage controls

For a valid labelled pixel `i` under condition `q`, use the same ground truth
and loss for both frozen experts:

`benefit_i(q) = CE(R01_RGB_i, y_i) - CE(R05_RGB_DSM_i(q), y_i)`.

Positive values favour R05; negative values mean R05 has higher loss. Keep the
continuous target and report positive-benefit and harm labels separately. Define
the neutral interval and any minimum-effect threshold before inspecting D9
results; report a zero-threshold sensitivity analysis. The oracle may use labels
only for scoring and an upper bound, never as a predictor input. Include an
argmax-correctness benefit definition as a sensitivity analysis because CE can
change without changing a segmentation decision.

Use identical pixels, masks, label remapping and spatial alignment for both
experts. Exclude ignored/boundary labels according to the frozen metric protocol.
Track class, connected-component size, tile, seed and corruption family. For
regional results, use spatial blocks or connected objects as analysis units;
correlated pixels are not independent replicates. Do not fit a predictor or
calibrator on a tile that is later scored as held out. Because R01/R05 were
trained on Train16, fitting on their Train16 predictions is in-sample and cannot
be treated as an independent performance estimate. A two-tile Val2 cross-fit is
exploratory only; freeze a new source before confirmatory claims.

## Frozen comparison ladder

Compare these feature families under the same evaluation rows and calibration
procedure. State the score direction before results are read.

1. Maximum softmax confidence and predictive entropy for each expert; include
   the previously tested D5 SafeMaxConfidence policy as a practical control.
   For direct benefit ranking use `maxprob(R05)-maxprob(R01)` and
   `entropy(R01)-entropy(R05)` so larger scores always predict more DSM benefit;
   report each expert's raw value as a secondary diagnostic.
2. SGMA-style multi-scale class-prototype similarity. Construct prototypes
   from training labels/features only, with no Val2 label access.
3. Frequency and image-quality descriptors computed from observable RGB/DSM
   inputs; use local and multi-scale measures, with fixed normalization learned
   on training data only.
4. Semantic plus frequency features.
5. Semantic plus frequency plus expert disagreement: predicted-class mismatch,
   probability divergence, confidence/margin differences and logit-residual
   magnitude. Both experts must be available when this group is evaluated.
6. Label-informed pixel oracle, explicitly an unattainable upper bound.

For combinations requiring fitted weights, freeze a simple regularized model,
feature normalization, spatially disjoint fitting/calibration/evaluation split,
and hyperparameter budget before evaluation. Report direct, unfitted scores
alongside fitted combinations. A complex predictor is not justified by D9.

## Conditions and measurements

First evaluate clean DSM plus global and local DSM missing, blur, downsampling,
noise and spatial misalignment. Record severity, mask shape, damaged/interior/
boundary region and exact random seed. The first-stage target is **DSM marginal
benefit**; RGB corruption and RGB missing are required in a later bidirectional
extension and must be specified before claiming arbitrary-modality robustness.
When DSM is completely absent, availability is known and the deployed policy
must choose R01 deterministically. Do not call detection of a synthetic zero
fill a learned missing-modality detector.

Primary diagnostic metrics: AUROC and AUPRC for both benefit and harm, ECE and
reliability diagrams for calibrated benefit probability, and benefit prevalence.
Primary decision metrics: negative-transfer rate and magnitude, NB mIoU fg5 and
FullGT mIoU fg5 for the routed prediction versus R01, R05, D5 and the oracle.
Define the negative-transfer denominator and loss/mIoU aggregation explicitly in
the implementation record. Stratify by class, component size, degradation type,
tile and seed. Report raw counts. Use tile/scene-level uncertainty where there
are enough independent units; do not calculate pixel-independent p-values.

## Entry gate for safety-gate training

No safety-gate training follows D9 unless semantic+frequency+disagreement
improves both seeds over the best of confidence, entropy and semantic-only on both
benefit AUROC and AUPRC by at least 0.02 absolute each, and improves both Val2
tile directions. For a calibrated threshold chosen only on the fitting split,
its selected-dual negative-transfer rate must fall by at least 10% relative
to D5 while NB mIoU falls by no more than 0.3 pp and ECE rises by no more than
0.02 absolute. Also report harm ranking and clean/degraded strata; no severe
degradation family may show a greater than 0.3 pp NB mIoU loss to D5. These
are development-screen margins, not statistical significance thresholds.
The exact new independent evaluation source and fitting/calibration partitions
must be registered before fitting a combination. The new source is required
to confirm the effect before safety-gate training or paper claims. A gate that
merely reproduces the D5 confidence policy does not establish a new mechanism.
If the evidence fails, retain D9 as a negative diagnostic and stop this route.

The entropy control was added to this entry gate after the D9A read-only
ranking review and before any fitted combination was specified or trained.
It makes the comparison stricter; D9A Val2 cannot serve as the independent
confirmation source.

If the gate passes, the candidate model is

`Zsafe = ZRGB + availability_DSM * gate * (Zdual - ZRGB)`.

For `availability_DSM=0`, the output must equal `ZRGB` exactly. This identity
requires a unit check before any robustness evaluation. First validate DSM
benefit; add symmetric RGB-missing handling only under a separate protocol.

## Execution rules

### D9A initial runnable stage

`scripts/run_rebuild_v1_d9a_queue_20260923.sh` performs a seed42 clean smoke
check, followed by independent condition stages for both frozen expert seeds.
It covers clean DSM, global zero/down8/blur5/noise (Gaussian sigma 0.10 on
normalized DSM), 4-pixel right shift, and quadrant-1 local zero/down8. Each
stage computes true-class CE benefit on a fixed uniform sample of up to 200,000
valid NoBoundary pixels per tile. It reports exact tie-aware AUROC/AUPRC of
unfitted confidence, entropy and expert-disagreement scores, plus full-tile
R01/R05/D5/correctness-oracle mIoU. The same sampled pixel locations are used
across seeds and conditions. A 0.01-CE neutral exclusion and a zero-threshold
sensitivity result are both reported. Selected-dual harm is the fraction of
selected pixels whose CE benefit is below -0.01. All scores and groups report
support counts.

D9A does not output ECE because these unfitted scores are not calibrated
benefit probabilities. Semantic-prototype and frequency combinations, ECE and
the entry gate above require the separately frozen fitting and evaluation
source. D9A results alone cannot pass the full D9 gate. Every D9A stage is
read-only with respect to checkpoints and datasets, writes only compact metrics
under project `records/`, and has a separate timeout and failure-continue log.

Any inference job must use physical GPU 0 only (`CUDA_VISIBLE_DEVICES=0`, logical
`cuda:0`). All generated features, logits, logs and records stay under
`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro`; do not upload full logits,
datasets or weights. Each condition is an independent queue stage with a timeout;
record its failure and continue with the next condition. A summary may claim
completion only for observed, successful stages. Run the repository execution
boundary validator before launch.
