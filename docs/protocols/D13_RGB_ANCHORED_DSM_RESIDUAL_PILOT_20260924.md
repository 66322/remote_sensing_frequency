# D13 proposal: RGB-anchored DSM residual training pilot

Status: design proposal only. No implementation, server queue, trained model, or validated result exists. This is a new training mechanism after the failed D11/D12 frozen-expert benefit-head screens, not a relaunch of those screens. The historical Test6 remains frozen.

## Question and evidence level

Can a trainable DSM correction to a frozen R01 Optical/RGB expert retain useful DSM information while reducing predictions that R01 got right and the corrected output gets wrong? This is an exploratory Potsdam experiment. Train16 was used to train R01, and Val2 has repeatedly guided this project; neither pixel counts nor the two Val2 tiles provide an independent generalization claim. An independent scene source remains necessary before a final paper claim.

## Model and matched comparisons

Freeze the seed-matched R01 weights and forward path. Let `z0` be its logits, `a` a recorded DSM-availability mask, and `r` a learned correction. Compute `z = z0 + a * r`. For known complete or local absence, explicitly return/copy `z0` on absent pixels and test numerical equality. This is structural fallback only; it does not guarantee safety where DSM is present.

Stage 1 uses the same residual architecture, optimizer, crop stream, training steps, corruptions, and seed for each arm:

1. **RGB-capacity control:** the same residual network receives RGB/R01 inputs but no DSM information. This measures added trainable capacity.
2. **DSM-CE:** the residual network receives DSM and uses segmentation cross-entropy only. This tests whether the DSM residual provides information beyond capacity.
3. **DSM-risk:** identical inputs and capacity to DSM-CE, with an additional loss on pixels where frozen R01 is correct: `CE(z,y) + lambda * 1[R01 correct] * max(0, CE(z,y)-CE(z0,y))`. This is a differentiable surrogate for avoiding new errors, not a proof that argmax harm is bounded. Fix `lambda` and all loss reductions before Val2 evaluation; do not search them on Val2.

Use seed 42 and seed 17 with their corresponding frozen R01 experts. Initial training is a fixed, short pilot with final-step checkpoints; estimate runtime and memory with a smoke run before freezing the step count. Do not choose a favorable checkpoint, threshold, or corruption weight from Val2. Evaluate each completed arm on identical full-image Val2 pixels and paired corruption instances.

Only if Stage 1 shows a reproducible benefit of DSM-risk over both controls should Stage 2 compare learned semantic-only, frequency-only, and semantic+frequency conditions. Include a capacity-matched no-semantic/no-frequency head. Keep the DSM-risk loss, data, schedule, and seeds fixed. A larger network or additional parameters alone must not be credited to semantic/frequency evidence. Do not force a frequency branch into the final model if it has no stable increment.

## Development conditions and measurements

Keep Optical/RGB available in this first phase. Include clean DSM, known complete and local absence, blur, downsampling, Gaussian noise, and spatial shift using the same paired instances across arms. Preserve the existing NoBoundary `mIoU_fg5(full)` as the primary development metric and also save FullGT `mIoU_fg5`, int64 6x6 confusion matrices, class counts and IoU, per-tile metrics, and corrected/rescued pixel counts. In particular report `R01 correct -> model wrong` and `R01 wrong -> model correct` separately, by class and corruption; report Car and Building separately. The independent unit for comparison is a scene/tile, not a sampled pixel.

The Stage 1 continuation decision must be frozen before server training: require DSM-risk to improve the prespecified condition-average NoBoundary mIoU over the stronger matched control in *each* seed, reduce new-error counts without erasing most rescue, retain exact known-missing fallback, and avoid a severe-noise or clean regression hidden by the mean. Fix numerical margins and the corruption weights in the executable protocol after smoke-based feasibility estimates, before examining Val2 D13 results. If either seed fails, stop Stage 2 and archive a negative result. A positive exploratory gate permits full-image development analysis, not a final safety or independent-test claim.

## Execution and provenance

Before a queue exists, review the actual R01 feature/logit call path and training data flow, freeze configs and source hashes, add a fallback unit test and one-batch gradient/smoke check, and document an expected GPU-hour budget and stop conditions. Run only on physical GPU 0, write runtime artifacts only under `/home/jovyan/zzx`, continue independent queue stages after a failure, and never load Test6. The user starts the server queue manually after pulling the committed implementation; no server job is started by this proposal.

