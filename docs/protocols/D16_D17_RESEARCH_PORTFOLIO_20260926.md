# Post-D15 research portfolio: intervention learning and geometry supervision

Status: **implemented exploratory designs, awaiting server launch and CUDA smoke**. User requested a
larger useful batch, two physical GPUs 0/1, one day or longer. This supersedes
the proposed pivot to low-resolution feature recovery after D15. The research
problem remains RGB-DSM complementary semantic segmentation under variable
modality usefulness. RGB down4 is one stress condition, not a new SR task.

## Investment decision

D15 establishes useful DSM information and cross-seed down4 gains for the
existing R05 baseline. It does not establish a new method or learned utility
predictor. D11/D12 selectors, D13 frozen-RGB output risk residual and unchanged
B1-B4 distillation are closed. Give end-to-end complementary learning one
bounded mechanism batch, with an independent geometry-supervision alternative.
If neither works, stop tuning this architecture/loss family and move to a
matched pretrained-representation experiment. No unlimited Val2 sweeps.

## Mandatory matrix: eight configurations x two seeds = sixteen trainings

All are **4000-step continuation pilots**, not newly trained-from-scratch
16k baselines. Initialize A0-A3/B1-B2 from the same R05 checkpoint within each
seed; A4/A5 from the same matched C-OO-QD checkpoint. Seeds42/17. Use the same
crop/treatment sequence, effective batch16, optimization schedule, two-view
supervised loss, and fixed final checkpoint. Existing B1/D13 continuations do
not substitute for these newly changed controls. Backbone and fusion are
trainable; this does not reuse the frozen D13 residual architecture.

| Arm | Input model | Additional training objective | Question |
|---|---|---|---|
|A0|R05|None; supervised clean and intervened views|Matched continuation/augmentation control|
|A1|R05|Unmasked clean-to-intervened consistency|Does generic consistency suffice?|
|A2|R05|Task-conditioned consistency|Does targeted supervision preserve useful corrections?|
|A3|R05|Class/count-matched shuffled consistency mask|Does meaningful mask placement beat generic reweighting?|
|A4|C-OO-QD|Same supervised two-view control|RGB capacity/augmentation control|
|A5|C-OO-QD|Same task-conditioned consistency as A2|Is improvement specific to DSM rather than regularization?|
|B1|R05|RGB-feature auxiliary DSM-gradient supervision|Can geometry supervision improve the learned representation?|
|B2|R05|Same auxiliary head with spatially shuffled geometry targets|Does aligned geometry matter?|

For D16, every sample has a clean view and a view with one input perturbed.
Supervise both with the original semantic labels; all arms receive identical
supervised views and average their CE losses. A1-A3 use stop-gradient clean
predictions as consistency targets. A2 applies consistency only at valid
training pixels where the clean prediction is correct and the perturbed
prediction is wrong; completely unavailable auxiliary regions are excluded
from this consistency term but still receive semantic CE. A3 preserves the
selected count per class while shuffling mask positions. Targets/masks use
Train16 labels only and are absent at inference. This is a correctness-aware
regularizer, not ground-truth causal utility, a calibrated risk estimate or a
newly proven algorithm. All-pixel consistency is deliberately included because
it may be as good or better. R05 and C-OO controls must implement matched
second-stream intervention semantics and document when an intervention means
DSM damage versus grayscale-view damage.

For D17, predict normalized DSM horizontal/vertical gradients through a small
auxiliary head attached to the RGB stream **before any DSM mixing**. Use the
original geometrically aligned DSM target before corruption; never predict
DSM from a fused tensor that already contains it. Remove the head at inference.
B1/B2 share head size, target scaling, loss weight and optimization. Gradients
describe DSM geometry, not semantic edges or nDSM heights. The no-auxiliary
A0 baseline distinguishes auxiliary supervision from ordinary continuation;
B2 checks whether spatial alignment provides more than generic regularization.
This is an alternative to confidence-based teacher distillation tested in B1-B4.

Exact treatment probabilities, optimizer values and loss coefficients must be
written into executable configs before any run. Use one fixed coefficient per
loss, no post-result grid search. Do not combine A2 and B1 in this batch: first
measure their independent effects. Training must use separate RNG streams for
augmentation and new-head initialization so the matched data sequence survives
differences in auxiliary computation.

Frozen executable config: `configs/rebuild_v1/d16_d17_portfolio_20260926.json`.
Microbatch2 x accumulation8 = effective16, two supervised views per example;
4000 continuation steps; backbone LR2e-5, decoder/head multiplier10, AdamW,
100-step warmup followed by linear decay; consistency0.2, geometry0.1 with
gradient scale0.1. Treatment probabilities: clean0.2 and each of the four RGB
quality, two auxiliary quality, two auxiliary absence treatments0.1. Random
crops/flips use the original R05 settings and a separate step-keyed RNG.
Geometry loss uses the clean view. B2 shuffles paired x/y targets spatially
within each sample. These choices are frozen before new result collection.

## Evaluation and stopping

Evaluate clean, RGB down2/down4/blur/localdown, DSM quality degradation and
global/local known absence. RGB and DSM perturbations are separate families;
down4 is not the sole selection target. Save NoBoundary foreground-five mIoU
as primary, FullGT and six-class diagnostics, int64 confusion matrices, per-tile
and per-class metrics, and harm/rescue relative to the same-condition R01.
Report raw missing-DSM performance and any deterministic availability fallback
separately; fallback gains are not learned robustness.

Proposed continuation screen to freeze in configs before launch:
- Macro-average three equally weighted families: clean, RGB quality, DSM
  quality. Average conditions within a family, not all rows together.
- A2 must beat its relevant A0/A1/A3 controls in both seeds, with at least
  +0.2pp over the strongest control in the primary macro score. Compare
  A2-A0 against A5-A4 before claiming a DSM-specific mechanism.
- B1 must beat both A0 and B2 in both seeds by the same +0.2pp screen.
- Clean must not fall more than0.1pp below A0; report each tile and reject a
  broad robustness claim if a family loses more than0.3pp. A candidate passing
  pooled thresholds can still warrant rejection after these predefined guards.
- The same guards apply per tile: clean loss <=0.1pp and each family loss
  <=0.3pp versus A0; they are encoded before launch, not applied retrospectively.
- For a claim of reduced negative transfer, require harm to improve while
  retaining at least90% of matched-control rescue in the predeclared DSM-quality
  family; do not reinterpret reduced use of DSM as safer benefit selection.
- If neither hypothesis passes, close these specific variants. No new lambda
  sweeps, no D13 restart, no frequency stacking as an automatic rescue.

These are engineering investment thresholds, not significance guarantees.
Two repeatedly inspected Val2 scenes cannot establish generalization. A passing
method needs a new matched longer-budget protocol, additional seed and a
geographically independent labelled source before confirmatory thesis claims.
Test6 remains prohibited. Source acquisition is bounded parallel preparation,
not an excuse to block exploratory training or retry the same failed download.

## Two-GPU execution requirements

Implement a shared ready-job queue for GPU0/GPU1, rather than assigning all
evaluations to GPU1. Every training job immediately schedules its evaluation;
an idle worker takes the next independent ready job. Alternate seed/GPU
assignments across arms. A failed per-job evaluation retains its checkpoint,
writes a diagnosis and does not discard unrelated jobs; a shared data/split/
metric fault pauses affected dependent work. Never mark incomplete results as
an experimental negative. Retry at most once for a demonstrated transient
failure, not for a scientific gate failure.

Before the long batch, verify train -> checkpoint -> reload -> deterministic
clean evaluation on both GPUs, and exercise worker start/resume/error paths.
Reuse D15 outputs; no repeated D15 matrix. Save model/optimizer/scheduler state,
step and all RNG state, source/config binding, per-job start/end/throughput.
Use completed manifests to skip done work and checkpoint signatures to resume.
At24h emit a progress summary and continue unfinished finite jobs. A rough
budget is 16 pilot trainings, 64k total optimizer steps: approximately12-30h
on two cards including evaluation, subject to actual two-view throughput.
Re-estimate from the first100 steady-state steps, including scheduled evaluation.
Never present that estimate as an observed completion time.

## Reserved next direction: pretrained representations / efficient adaptation

If A/B fail, or to independently check a representation bottleneck after the
batch, prepare one frozen pretrained RGB backbone and a lightweight decoder/
adapter. Use three matched variants (RGB, RGB+grayscale auxiliary adapter,
RGB+DSM auxiliary adapter) x seeds42/17 = six runs. Keep the same new pretrained
source and budget across these variants. An improvement over old R01 alone
cannot attribute benefit to DSM. Verify legal weight access, input normalization,
bands and license before scheduling; failed acquisition must not stall A/B.
Do not start DINO, SAM, MoE and multiple new backbones simultaneously.

Dynamic/sparse computation follows a useful model: to save compute, skip work
before the expensive branch, then report measured latency/memory/accuracy.
Output gating after both branches run does not establish efficiency. Open
vocabulary and image restoration require different problem definitions and
remain future options, not automatic extensions of D15.

Related primary sources (precedents, not novelty endorsements):
- [Sample-level modality valuation](https://arxiv.org/abs/2309.06255).
- [DFormer, RGBD representation pretraining](https://arxiv.org/abs/2309.09668).
- [DFormerv2, geometry priors](https://arxiv.org/abs/2504.04701).
- [Keep the Balance, parameter-efficient RGB+X adaptation](https://github.com/imcjx/KTB).

RGBD camera depth and overhead DSM are not interchangeable physical inputs;
these papers motivate comparisons, not an assumption that their results carry
over. Claims attached to unverified 2026 titles in earlier notes are not used
to establish novelty or decide the experiment gate.

## Server launch and observation

Compatibility repair after first server attempt: last observed stop15:29:20
+08:00, 2026-09-26. Eight smoke jobs failed before the first optimizer update
because the server PyTorch rejects CUDA NLL2d forward under strict determinism.
Use one-hot/log-softmax mean-valid-pixel CE for both views; this preserves the
unweighted CE objective and its gradients and avoids NLL2d and gather backward.
Do not use warn_only or disable strict determinism. Added CPU value/gradient
equivalence and a strict CUDA forward/backward regression in server preflight.
Failed smoke directories have no checkpoints; relaunch reuses the directories
and appends logs. No formal training or experimental result was produced.

Local validation: ten CPU tests passed, including real pre-fusion independence,
teacher stop-gradient, missing-region exclusion, shuffled control counts,
noise reproducibility, atomic checkpoint/optimizer/RNG resume, and shared-worker
failure isolation. Entry imports and Python syntax checked. Server weights,
raw images and CUDA are unavailable on this computer; CUDA end-to-end checks
are mandatory in the queue before formal jobs, and are not yet observed.

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
conda activate remote_sensing
git pull --ff-only origin rebuild-v1-protocol-20260915
mkdir -p records/rebuild_v1_d16_d17_queue_20260926
nohup bash scripts/run_rebuild_v1_d16_d17_queue.sh > records/rebuild_v1_d16_d17_queue_20260926/launcher.log 2>&1 &
```

The launcher checks tracked source, inputs, three existing model families,
physical GPUs0/1 and free workspace capacity (80GiB on first launch; reserve
decreases for already saved checkpoints when resuming). Eight one-step smoke jobs
cover every loss branch (four on each GPU), save/reload their checkpoints and
repeat deterministic clean inference on a 512px Val2 crop. Any smoke failure
stops formal launch. Passing smokes automatically start 16 full 4k pilots and
their nine-condition, two-tile evaluations. Smokes are excluded from decisions.
Each worker takes the next shared job and immediately evaluates its own training.
Completed work is bound to source/config/checkpoint hashes and reused; interrupted
training resumes the last100-step state and interrupted evaluation reuses completed
condition files. A code/config mismatch stops reuse rather than silently mixing.
One failed formal job does not stop independent jobs. No automatic scientific
retry. Restart the same launcher after diagnosis, keeping bound source unchanged.

```bash
tail -n 20 records/rebuild_v1_d16_d17_queue_20260926/status.tsv
tail -n 30 records/rebuild_v1_d16_d17_queue_20260926/launcher.log
cat records/rebuild_v1_d16_d17_queue_20260926/SUMMARY.log
```

Final success: `QUEUE FINISHED jobs=16 failures=0 summary_ok=True`, decision
status COMPLETE and missing=[] in `records/rebuild_v1_d16_d17_20260926/decision.json`.
At24h a progress line is written and unfinished finite work continues. Runtime
estimates remain provisional until the first100 full optimizer steps; dual-stream
two-view work may exceed the earlier12-30h rough estimate. Do not promise24h completion.
Reserved pretrained-adapter runs are not part of this executable queue.
