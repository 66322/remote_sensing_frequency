# D9A follow-up: matched entropy-routing decision audit

## Why this evaluation is needed

D9A showed that entropy difference ranks CE-defined DSM benefit above
confidence difference in all 16 seed-by-condition rows, but rank quality does
not establish routed mIoU or lower negative transfer. D5's original seed42/17
logs report completion; its expected per-seed metric directories and queue
status file are absent from project records in the user-supplied server audit.
This narrowly scoped evaluation measures a previously unreported decision
outcome. It does not recreate or replace the historical D5 source files.

## Frozen design

- Use only the existing R01 true RGB-only and R05 RGB+DSM experts at seeds 42
  and 17; do not train or update them.
- Use exactly Val2 tiles `3_11` and `5_10`, the D9A label mapping, full and
  NoBoundary metrics, and the same eight D9A DSM conditions. Never load Test6.
- Compare R01, R05, the corrected D9A `safe_confidence` route, raw D5-style
  `min_entropy` and `safe_entropy`. The first and last safe routes force R01
  only where DSM is known to be missing; downsampled DSM remains available.
- `safe_entropy` selects R05 when its predictive entropy is strictly lower
  than R01's. Ties select R01. `safe_confidence` selects R05 when its maximum
  softmax probability is strictly higher. Ties select R01.
- Score mIoU fg5 and class IoU on all valid full and NoBoundary pixels, plus
  NoBoundary mIoU separately inside and outside each defined local region.
  On the same deterministic D9A sample positions, report selected-dual
  CE-harm rate, harm per valid pixel, mean harm magnitude and support by class,
  component-size bin, local damaged region, tile, seed and condition.
  Selected-dual harm means benefit below -0.01 CE among selected R05 pixels.
- Validate the frozen R01, R05 and safe-confidence mIoU against D9A, using
  corrected `fix1` outputs for local down8. Reject the summary if any control
  differs by more than 1e-4 absolute mIoU. Validate exact R01 fallback for
  both safe routes when DSM is fully absent.

This is an **exploratory** Val2 comparison: both tiles were used repeatedly
for development. Report every condition and both seeds; do not tune a
threshold, select a severity, fit a calibrator or claim independent test
performance from this stage. Entropy is an existing baseline, not a new
method. A gain would only make it a stronger control for later benefit-aware
models on a separately frozen evaluation source. A loss would stop the
simple entropy-route direction; it would not prove semantic/frequency benefit
prediction impossible.

## Execution

`scripts/run_rebuild_v1_d9a_entropy_route_queue_20260923.sh` performs one
seed42 clean smoke check and 16 independent seed-by-condition evaluations.
Every stage has its own GPU0 boundary check, timeout and failure record; one
failed stage does not block the rest. Outputs stay under project `records/`
within `/home/jovyan/zzx`. After a zero-failure queue, run
`scripts/summarize_rebuild_v1_d9a_entropy_route.py`, which source-hashes the
original per-stage metrics and compares them to the frozen D9A controls.
