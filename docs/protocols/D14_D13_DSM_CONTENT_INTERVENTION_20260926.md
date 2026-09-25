# D14: inference-only DSM content intervention for D13

Status: protocol and queue prepared on 2026-09-26; server execution pending.
D13 Stage 1 failed, and Stage 2 remains closed. D14 is a diagnostic of the
existing frozen Stage 1 checkpoints, not a new model candidate.

## Question and fixed comparisons

Does changing DSM **content** alter the D13 head's predictions while the
recorded availability mask remains present? The D13 eight-arm Val2 source
summaries are committed in `records/rebuild_v1_d13_compact_20260925/`.
They show very small differences among routine DSM degradation conditions,
which cannot establish that the head ignores DSM.

Use all four Stage 1 arms (RGB-CE, DSM-CE, RGB-risk, DSM-risk) and seeds 42/17.
The RGB arms are negative controls: their second stream remains the same
Optical-gray input in every D14 condition. Freeze the final 4000-step D13
heads, seed-matched R01 anchors, preprocessing, full-image Val2 tile pair
`3_11`/`5_10`, stride and inference batch. No training, checkpoint selection,
parameter tuning, or Test6 access.

For each DSM arm and tile, compare exactly three predefined inputs:

1. `clean`: original DSM.
2. `zero_present`: DSM values set to zero while **availability stays true**.
   This is intentionally distinct from the known-missing fallback.
3. `shift_half`: circularly shift DSM by half the tile height and width,
   preserving its values but disrupting correspondence with Optical.

The same conditions are labelled for RGB controls, but their actual input
stays fixed. Report full and NoBoundary pooled and per-tile 6×6 int64
confusion matrices, `mIoU_fg5`, harm H and rescue R relative to frozen R01,
and the fraction and true-class counts of valid pixels whose predicted
class changes versus clean. A prediction flip is a sensitivity measure,
not proof of a useful DSM contribution. Zero response at argmax level
does not prove logits or internal features ignore DSM.

## Checks and interpretation

Before any formal result, verify the source summary's D13 commit, config,
training source, evaluation source, 4000 steps, checkpoint SHA-256, and
R01 anchor SHA-256. The clean condition must reproduce the corresponding
original D13 full-image confusion matrix and harm/rescue counts exactly.
Every RGB control must have zero flips under both nominal interventions.
Any mismatch invalidates the affected run and stops interpretation.

This has **no continuation gate** and must not select a favorable
intervention. Describe both seeds and both Val2 tiles. If DSM arms show
zero or tiny class-decision response, conclude only that these frozen heads
have little *observed decision-level* dependence under the chosen
interventions. If they respond, inspect whether changed decisions help or
harm under each scene; neither result reverses D13's failed benefit gate.
`zero_present` and `shift_half` are diagnostic counterfactuals and may
be outside the training distribution. Val2 has been repeatedly inspected,
so this remains exploratory and cannot support generalization or safety
claims. Independent labelled scenes are still needed for confirmation.

## Execution

The queue is `scripts/run_rebuild_v1_d14_intervention_queue.sh`, with
configuration in `configs/rebuild_v1/d14_dsm_intervention_20260926.json`.
It runs on physical GPU 0 only. Runtime output is confined to
`records/rebuild_v1_d14_intervention_queue_20260926/` and
`records/rebuild_v1_d14_dsm_intervention_20260926/` under the project
root. It runs boundary and CPU checks, two Train16-crop smoke evaluations
without Val2, then at most eight independent full-image evaluations and a
summary. Each evaluation has a 10-minute timeout and the queue has a
one-hour wall cap. D13's eight-condition evaluations took about three
minutes each on the server; D14's three conditions are expected to fit
within the cap, but this is an estimate, not a measured guarantee. Stop
on shared preflight/smoke failure; record independent evaluation failures
and leave partial results. Do not relaunch into existing output directories.

Review `status.tsv`, `D14_SUMMARY.log`, and
`records/rebuild_v1_d14_dsm_intervention_20260926/decision.json`.
The status `FINISHED` line alone is not proof of complete data. Small
result JSON files may be copied to GitHub after completion; checkpoints
and raw datasets must remain on the server.
