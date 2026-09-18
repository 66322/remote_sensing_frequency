# REBUILD_V1 lightweight DSM / training-side screening addendum — 2026-09-16

Status: screening addendum; does not replace the frozen REBUILD_V1 causal protocol.
Branch: `rebuild-v1-protocol-20260915`

## 1. Why this addendum exists

The 16k R02 budget pilot is now closed and the complete schedule is frozen at 16k. The next formal causal requirement remains R01 Optical-only so that clean and degraded Fusion Gain can be measured.

A second, parallel research question is worth screening because the current R02 architecture maintains substantial modality-specific processing before the final decoder fusion:

> Does DSM require a full deep auxiliary encoding path to provide its useful segmentation information, or can most of the DSM benefit be retained with substantially lower inference cost?

This is a precision-vs-compute question. It is not a claim that lightweight DSM guidance is novel by itself.

## 2. Non-negotiable constraints

- Keep the frozen Train16 / Val2 split.
- Keep seed 42 for screening.
- Keep the frozen complete 16k schedule for all trained screening models.
- Do not spend multi-seed compute during first-pass screening.
- Final retained configurations must later be rechecked with additional seeds (planned: 17 and 2026).
- Historical TEST6 remains excluded from development/model selection.
- Do not cross every candidate with Q/D/Rare30/frequency variants during first-pass screening.
- Do not relabel tile-wise min-max DSM as metric depth. Initial geometric quantities must be described as relative-height / spatial-relation cues unless metric-height provenance is explicitly restored.

## 3. Immediate order

### P0 — no-retraining compute audit of R02

Run before designing pruning or lightweight blocks.

Questions:

1. How much wall-clock inference time is spent in the multimodal embedding/backbone/Transformer, decoder, and sliding-window/data-movement path?
2. How much GPU memory is used by the model-only path and whole-tile inference path?
3. What are total parameters and the parameters attributable to DSM-specific components?
4. Under one frozen geometry/precision/batch setting, what is the whole-tile latency/throughput?

Required timing protocol:

- H100 GPU0;
- FP32 first reference;
- fixed patch 512;
- fixed validation stride 256 for REBUILD_V1 development timing;
- fixed inference batch;
- warm-up before measurement;
- CUDA synchronization around timed model sections;
- report model-only crop latency separately from end-to-end tile latency;
- report median and spread over repeated measurements;
- do not compare timing numbers produced with different strides/batches/precision.

Engineering speedups that are mathematically/prediction equivalent should be applied symmetrically to all compared models and should not be claimed as the scientific contribution.

### R01 — genuine Optical-only formal baseline

R01 remains the first required new training run.

It must answer both:

- accuracy: what can Optical alone achieve under the matched 16k protocol?
- efficiency: how much compute/latency disappears when the DSM path is genuinely absent?

R01 is required before a lightweight-DSM method can be evaluated as retaining a fraction of DSM benefit.

Define clean DSM benefit of R02 as:

`Fusion Gain_clean = metric(R02_clean) - metric(R01_clean)`.

For a lightweight DSM candidate L, report both absolute accuracy and retained DSM benefit relative to R01/R02, rather than only L-vs-R02 delta.

## 4. Candidate training screens after P0 + R01

### G-S — spatial-relation control without DSM information

Purpose: isolate any gain caused by changing the attention/spatial relation formulation itself.

G-S must not consume DSM values. It is a structural/spatial-prior control.

Without G-S, a G-H gain cannot be attributed to DSM-derived relative height cues.

### G-H — lightweight DSM relative-height guidance

Purpose: test whether DSM can act as a low-cost auxiliary relation prior rather than a full deep feature stream.

Initial interpretation must be conservative because current DSM preprocessing uses tile-wise min-max normalization:

- acceptable wording: relative height, local elevation relation, normalized height difference;
- avoid: metric 3D distance, camera geometry, absolute-height geometry unless supported by raw-data provenance and preprocessing.

First comparison:

- R01 Optical-only
- R02 full dual path
- G-S spatial-only control
- G-H spatial + DSM relative-height relation

Only if G-H shows a useful accuracy/latency tradeoff should a small-DSM-CNN + simple fusion baseline be added to test whether the benefit comes from the proposed relation design or merely from using a cheaper DSM branch.

### A1 — training-side auxiliary semantic supervision

Purpose: test whether a training-only auxiliary objective improves optimization/modality utilization without adding inference-time heads.

A1 is a strong training baseline, not automatically a methodological contribution.

Because the current dual streams already interact inside the multimodal Transformer, any auxiliary branch loss must not be described as fully independent single-modality supervision unless the graph actually isolates that modality.

## 5. What is deliberately deferred

### R03 / R04

R03 quality-corruption training and R04 modality-dropout remain part of the frozen causal matrix and should still be run after R01/R02 establish Fusion Gain. They are not prerequisites for P0 profiling or code preparation of G-S/G-H/A1.

Do not combine R03/R04 with G-H/A1 in the first screen.

### Token pruning

Do not start token-pruning training until P0 shows that Transformer/token processing is a meaningful end-to-end bottleneck.

If pruning is later opened:

- start with one fixed retention budget (e.g. about 75%);
- compare against a simple/random/task-agnostic retention control under exactly the same budget;
- report actual wall-clock speed, not FLOPs alone;
- account for token restoration needed by dense prediction;
- add object-size and boundary diagnostics if the claimed contribution is small-target/detail preservation.

## 6. Low-cost evaluation additions

For retained models, add without changing checkpoint selection:

1. FullGT boundary-aware metric(s) for boundary claims;
2. per-Val-tile metrics (`3_11` and `5_10`) to detect single-tile-driven gains;
3. object-size-stratified Car recall/IoU analysis if a small-object claim is pursued;
4. parameter count, peak memory, model-only latency and end-to-end tile latency for efficiency claims.

NoBoundary remains useful for the official-style eroded evaluation but cannot by itself prove boundary improvement.

## 7. Go / No-Go rules for the lightweight line

Proceed beyond screening only if all relevant conditions hold:

1. R02 has a positive, meaningful clean Fusion Gain over R01;
2. P0 shows that the removable DSM/deep multimodal path contributes meaningful compute/latency;
3. G-H beats G-S, so DSM-derived relation information contributes beyond the structural/spatial control;
4. G-H retains a useful fraction of R02's DSM benefit while materially reducing measured inference cost;
5. a small DSM CNN baseline does not explain the same tradeoff more simply (run this baseline only if G-H passes the first screen).

Stop the lightweight line if the compute savings are negligible, if R02's clean DSM benefit is negligible, or if a generic cheap DSM branch matches G-H.

## 8. Recommended execution priority

1. P0 R02 profiling — no retraining.
2. R01 Optical-only smoke gate and formal 16k training.
3. Compute R01 vs R02 clean Fusion Gain and matched efficiency gap.
4. If motivation remains strong, run G-S and G-H as the first lightweight pair.
5. Run A1 as a training-side baseline, preferably after R01 is stable.
6. Keep R03/R04 in the causal queue; do not cross them with new structures yet.
7. Open token pruning only if P0 establishes it as a real bottleneck.
8. Add extra seeds only for configurations that survive the first-pass gates.

## 9. Relationship to the main REBUILD_V1 question

This addendum creates a parallel efficiency-oriented screening line; it does not invalidate the existing harmful-fusion causal line.

Two possible publishable outcomes are intentionally separated:

- robustness/conditional-utility route: when does DSM help or hurt, and can simple robust training avoid harmful fusion?
- efficiency route: how much of DSM's useful signal can be retained without paying for a full deep auxiliary processing path?

The data should decide which line has the clearer, more reproducible effect. Do not combine them into one large architecture unless both are independently supported first.
