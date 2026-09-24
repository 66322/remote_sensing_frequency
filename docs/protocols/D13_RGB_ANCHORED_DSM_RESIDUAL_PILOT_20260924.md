# D13 proposal: RGB-anchored DSM residual training pilot

Status: overnight design specified on 2026-09-24; implementation and server smoke pending. No server queue, trained model, or validated result exists. The user requested multiple unattended experiments because they may not be available the next day. This is a new training mechanism after the failed D11/D12 frozen-expert benefit-head screens, not a relaunch of those screens. The historical Test6 remains frozen.

## Question and evidence level

Can a trainable DSM correction to a frozen R01 Optical/RGB expert retain useful DSM information while reducing predictions that R01 got right and the corrected output gets wrong? This is an exploratory Potsdam experiment. Train16 was used to train R01, and Val2 has repeatedly guided this project; neither pixel counts nor the two Val2 tiles provide an independent generalization claim. An independent scene source remains necessary before a final paper claim.

## Model and matched comparisons

Freeze the seed-matched R01 weights and forward path. Let `z0` be its logits, `a` a recorded DSM-availability mask, and `r` a learned correction. Compute `z = z0 + a * r`. For known complete or local absence, explicitly return/copy `z0` on absent pixels and test numerical equality. This is structural fallback only; it does not guarantee safety where DSM is present.

Stage 1 uses the same residual architecture, optimizer, crop stream, training steps, corruptions, and seed for each arm:

1. **RGB-capacity control:** the same residual network receives RGB/R01 inputs but no DSM information. This measures added trainable capacity.
2. **DSM-CE:** the residual network receives DSM and uses segmentation cross-entropy only. This tests whether the DSM residual provides information beyond capacity.
3. **RGB-risk:** the RGB-capacity control with the same additional loss used by DSM-risk. This separates a general regularization effect from a DSM-specific gain.
4. **DSM-risk:** identical inputs and capacity to DSM-CE, with an additional loss on pixels where frozen R01 is correct: `CE(z,y) + lambda * 1[R01 correct] * max(0, CE(z,y)-CE(z0,y))`. This is a differentiable surrogate for avoiding new errors, not a proof that argmax harm is bounded. Fix `lambda=1`; average CE and the masked penalty over the same valid training pixels. Do not search lambda on Val2.

Use seed 42 and seed 17 with their corresponding frozen R01 experts: four arms times two seeds gives eight mandatory training jobs. Fix 4000 optimizer steps per job, patch 512, effective batch 16, and use the final-step checkpoint. The server smoke measures runtime and memory before formal jobs, without reading Val2. If this budget does not fit, report infeasibility/incomplete work rather than shortening one arm or changing the schedule after seeing a result. Do not choose a favorable checkpoint, threshold, or corruption weight from Val2. Evaluate each completed arm on identical full-image Val2 pixels and paired corruption instances.

Only if Stage 1 passes in both seeds should Stage 2 compare learned semantic-only, frequency-only, semantic+frequency, and a capacity-matched no-semantic/no-frequency head. Four arms times two seeds gives eight optional training jobs, for at most sixteen total. Use dense frozen decoder features with trainable projections for the semantic candidate, rather than D12's channel-summary statistics. Frequency maps are candidate inputs, not labelled reliability. Freeze the exact feature/architecture definitions in the implementation before launching any D13 training. Keep the DSM-risk loss, data, 4000-step schedule, and seeds fixed. A larger network or additional parameters alone must not be credited to semantic/frequency evidence. Do not force a frequency branch into the final model if it has no stable increment.

## Development conditions and measurements

Keep Optical/RGB available in this first phase. Include clean DSM, known complete and local absence, blur, downsampling, Gaussian noise, and spatial shift using the same paired instances across arms. Preserve the existing NoBoundary `mIoU_fg5(full)` as the primary development metric and also save FullGT `mIoU_fg5`, int64 6x6 confusion matrices, class counts and IoU, per-tile metrics, and corrected/rescued pixel counts. In particular report `R01 correct -> model wrong` and `R01 wrong -> model correct` separately, by class and corruption; report Car and Building separately. The independent unit for comparison is a scene/tile, not a sampled pixel.

The primary evaluation matrix contains clean, DSM zero, local missing (quarter area), blur5, down8, local down8 (quarter area), normalized Gaussian noise std0.10, and shift16. Use equal weights for five available-DSM families: clean, blur, the mean of global/local down8, noise, and shift. Missingness checks are mandatory but excluded from the gain average so deterministic fallback cannot dominate it. Harm H and rescue R are counts divided by the same valid NoBoundary pixels (labels 0 through 5); retain classwise raw counts and denominators. Do not confuse this H with a rate conditional on selected pixels.

Stage 1 proceeds only when all eight final-checkpoint jobs and their paired evaluation records are complete and DSM-risk meets all of these exploratory criteria in *each* seed:

- at least +0.10 percentage points in the above family-average NoBoundary mIoU over the strongest of the other three matched arms;
- at least 10% less family-average H than DSM-CE, while retaining at least 90% of its family-average R; if DSM-CE has zero H, require zero H;
- worst tile-condition H no greater than 0.5%; clean pooled mIoU no worse than frozen R01; severe-noise pooled mIoU no more than 0.3 pp below R01;
- exact known-missing fallback, finite outputs, unchanged R01 weights, matched budgets, and complete provenance.

These are engineering continuation margins, not a power calculation or statistical safety guarantee. Do not relax them after seeing D13. If either seed fails, skip Stage 2 and use saved predictions/counts to report where harm and rescue occur. Failures, missing paired arms, time limits and incomplete evaluations are INCOMPLETE, never a negative scientific conclusion. A positive exploratory gate permits further development only, not an independent-test claim.

## Unattended 24-hour schedule

1. Preflight and a short training/gradient/fallback smoke; estimate duration and peak memory. A shared implementation or numerical failure stops formal training; a failure confined to one independent run is recorded and does not block other independent runs.
2. Complete Stage 1 matched seed blocks, their full-image evaluation and the decision summary. Interleave the seed blocks where practical and use deterministic, identical crop/corruption streams within each seed. Comparisons use only complete paired jobs.
3. Automatically enter Stage 2 only on a both-seed pass. Do not reinterpret a failed base gate as permission to try a larger head. If Stage 1 fails, produce per-tile/class/condition harm-rescue diagnostics from existing records and finish early.
4. For completed Stage 2 pairs, compare each added feature to the base and the capacity control. Attribute a semantic/frequency increment only if it repeats in both seeds; do not pick the best seed. Any extra held-out-corruption evaluation remains a development stress test, not independent confirmation.
5. Always attempt a final manifest and human-readable summary listing completed, failed, skipped and time-limited jobs, frozen checkpoints, metrics and next decisions. Preserve partial outputs. The total wall-clock limit is 24 hours; reserve the final three hours for pending evaluation and summaries and launch no optional training that is forecast to consume that reserve. Time allocations are planning caps, not measured speed promises.

No third expert seed, longer training budget, threshold sweep, or external-data acquisition is added automatically. Sixteen means the maximum number of training jobs, not sixteen independent scene replications. The user should need one server launch and may inspect the saved summary later; no intermediate manual gate approval is required.

## Execution and provenance

Before a queue exists, review the actual R01 feature/logit call path and training data flow, freeze configs and source hashes, add a fallback unit test and one-batch gradient/smoke check, and document an expected GPU-hour budget and stop conditions. Run only on physical GPU 0, write runtime artifacts only under `/home/jovyan/zzx`, continue independent queue stages after a failure, and never load Test6. The user starts the server queue manually after pulling the committed implementation; no server job is started by this proposal.
