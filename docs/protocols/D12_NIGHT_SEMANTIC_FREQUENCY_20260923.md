# D12 night experiment: deep context and frequency increment

Status: implementation prepared, server execution pending. This protocol
defines one exploratory batch following D11's failed linear screen. It trains
small three-outcome heads on frozen R01/R05 experts; no backbone, residual
segmentation gate, or historical Test6 is trained or evaluated.

## Question and controls

Do frozen decoder features improve the prediction of R05-only correct, R01-only
correct, or both wrong where the two experts disagree? Does local frequency
and structure add value beyond decoder context? The R05 decoder output is
fused optical-DSM context, not a pure DSM or SGMA prototype feature. The three
per-expert measurements are channel mean, mean absolute activation, and local
contrast at the final decoder output. They are matched to the exact inference
pixel with overlapping windows averaged. The nine frequency descriptors are
the prespecified D11 values.

Seven heads per seed: E, Ecap, ES, EF, ESF, ESF_shuffleS, ESF_shuffleF.
The first five are the primary comparison; the last two destroy the spatial
correspondence of one feature block within each tile/condition while retaining
the marginal values and other blocks. Ecap uses only expert features with a
wider hidden layer and more parameters than ESF. All heads use the same
three-outcome target, eight fixed epochs, AdamW, and the same matched samples.
The shuffled controls are mechanism diagnostics, not selectable candidates.

## Separation and evaluation

Use D11's six Train16 fit, two temperature-calibration, and two threshold-
calibration tiles. Reuse D11's 50k sampled coordinates and frozen probabilities.
Save each D12 model, temperature, and one condition-agnostic threshold before
reading Val2. Threshold selection maximizes mean rescue subject to empirical
H<=0.5% for every calibration tile-condition group. The configured grid is
0..1 in steps of 0.05. Evaluation reuses D10M's 200k-per-tile sampled Val2
coordinates and probability cache; new decoder features are extracted at
those exact coordinates. The pre-existing Val2 has been used repeatedly and
the experts saw Train16, so this remains development evidence.

Development conditions are clean, DSM blur5, and DSM Gaussian noise std0.10.
Evaluation adds circular shifts 4/16/32 and known DSM zero. Known absence
forces R01. The same seed/tile/condition pixel coordinates are used across
heads. Head fit, probability calibration, threshold calibration, and Val2
have nonoverlapping tile IDs, but not independent geography.

The sampled screen compares each core head with the better of calibrated D11
confidence and entropy in each condition; it averages clean, blur, noise,
and the mean of three shifts equally. Both seeds independently need +0.10 pp
sampled NoBoundary mIoU, clean no worse than R01, and worst Val2 tile-condition
empirical H<=0.5%. A candidate receives complete-image Val2 confirmation
only. At most two candidates proceed in prespecified order ESF, ES, EF, E,
Ecap; the shuffled controls cannot enter. Full-image confirmation prints
FullGT/NoBoundary confusion matrices, per-class metrics, harm, and rescue.
None of these screens constitutes statistical safety or independent testing.

## Execution and stop

The queue is serialized on physical GPU0 and writes under /home/jovyan/zzx.
It refuses to overwrite an existing run and stops on numeric/smoke failure.
Independent later failures are recorded while remaining jobs continue. Total
wall-clock budget is eight hours from start. Core head work has priority over
the two shuffled controls; full-image work runs only if a candidate passes.
Incomplete work is reported, never interpreted as a negative result.
Checkpoints, code commit, source-file hashes, threshold, metrics, and status
must be retained. The server still holds all large artifacts.
