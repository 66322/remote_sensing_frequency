# Next research decision after D14 (2026-09-26)

**D15 queued for user launch; server execution not yet observed.** The next exploratory batch is the two-GPU D15 DSM-only capability and RGB degradation evaluation in [`D15_DSM_CAPABILITY_RGB_DEGRADATION_20260926.md`](../protocols/D15_DSM_CAPABILITY_RGB_DEGRADATION_20260926.md). It trains two matched 16k DSM-only seeds, evaluates R01/R05/C-OO-QD under paired RGB degradation on both seeds, then summarizes a prespecified exploratory gate. The user's new authorization allows physical GPU0 and GPU1 and continuation beyond one day. After pulling this branch, run the launch command in that protocol. D15 results will choose the *next* method protocol; no untested recovery architecture or harm/rescue training is auto-launched.

**Current decision after D14, 2026-09-26:** D14 completed 8/8 paired
inference evaluations with no queue failures. It detects DSM
decision-level sensitivity but no stable mIoU benefit; D13's failed
gain/rescue gate is unchanged. Read
`docs/experiments/D14_RESULTS_20260926.md`. Do not relaunch D14,
run D13 Stage 2, or tune its risk penalty on Val2. The eight original
D14 summaries were transferred in commit `348dda6` and the per-tile/class
audit is complete. The subsequent research decision should focus on a
new method target and an independent labelled scene source before any
confirmatory claim. No GPU queue is currently specified. The older D14
launch instructions below are historical.

**Current decision, 2026-09-25:** D13 Stage 1 completed but failed its
prespecified two-seed gate; the queue correctly skipped Stage 2. No D13
relaunch or threshold adjustment. The eight full-image Val2 summaries were
transferred in commit `8236a07` and audited. Matched comparisons show a
small DSM-specific increment that reverses across seeds and a risk loss that
suppresses both harm and rescue. See
`docs/experiments/D13_RESULTS_20260925.md`. The next bounded question is
whether the trained DSM heads respond to DSM content when the availability
mask is held fixed. If pursued, predeclare a short inference-only
counterfactual protocol with matched RGB heads as a negative control and
paired full-image condition/class/tile metrics. Do not infer modality use
from the current near-invariant corruption results alone. A new training
objective requires its own protocol and an independent evaluation source
for confirmatory claims. Test6 remains frozen. All D13 launch instructions
below are historical.

**2026-09-24 runnable exploratory plan:** After reviewing D9-D12, the next concrete
method question is a staged RGB-anchored DSM residual training pilot, specified
in `docs/protocols/D13_RGB_ANCHORED_DSM_RESIDUAL_PILOT_20260924.md`.
Stage 1 compares matched RGB-capacity, DSM-CE, RGB-risk, and DSM-risk arms in
both seeds (eight runs); Stage 2 adds up to eight semantic/frequency/capacity
ablations only on a both-seed pass. The requested unattended plan has a
24-hour cap, fixed 4000-step runs, frozen numerical continuation margins,
automatic diagnostics on failure, and final summaries. The D13 queue is now
implemented; local CPU numerics and syntax checks passed, while server smoke
and GPU training are pending. It is a
new training mechanism, distinct from the failed D12 frozen-expert selector.
Potsdam Val2 can give exploratory development evidence only; an independent
scene source is still required for final confirmation. Do not use Test6.

After pulling this branch on the server, launch once from
`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro` in the `remote_sensing`
environment:

```bash
git pull --ff-only origin rebuild-v1-protocol-20260915
mkdir -p records/rebuild_v1_d13_residual_queue_20260924
nohup bash scripts/run_rebuild_v1_d13_residual_queue.sh > records/rebuild_v1_d13_residual_queue_20260924/launcher.log 2>&1 &
```

The queue performs its own GPU-boundary, numeric, training-smoke and
Train16-only evaluation-smoke checks before formal work. Later inspect
`records/rebuild_v1_d13_residual_queue_20260924/status.tsv`,
`D13_STAGE1_SUMMARY.log`, `D13_FINAL_SUMMARY.log` in that directory, and
`records/rebuild_v1_d13_residual_20260924/final_decision.json`. No manual
intermediate decision is required. The executable commands below under the
historical D12 heading are obsolete.

D12 completed 14/14 heads with zero queue failures and **no candidate** under
the prespecified two-seed gain/harm screen. Complete-image confirmation was
correctly skipped. The exact server-output transcription and interpretation
are in `docs/experiments/D12_RESULTS_20260924.md`. Do not relaunch D12 or
relax its Val2 thresholds after seeing the result.

The historical next step was a bounded decision memo using D9–D12 evidence: decide whether
a benefit-aware selector warrants a new experimental design. A new fitted
method needs a genuinely changed mechanism or supervision target and a frozen,
spatially independent labelled evaluation source. The repeatedly inspected
Val2 cannot serve as confirmation. Keep the question of DSM's marginal
decision value over RGB, but do not claim that this semantic/frequency head
solves it. Do not train a residual gate from the failed D12 selector, run Test6
evaluation, or launch another
same-source parameter sweep. The DFC19 proxy failure is not a reason for
another prolonged audit now. The launch instructions below are historical.

# Historical D12 launch plan (completed)

D11 finished on the server at 2026-09-23 18:51:37 +08:00 according to the user's pasted queue and summary. All 12 models completed with zero queue failures; none passed the predeclared two-seed screen. The result is transcribed at `docs/experiments/D11_RESULTS_20260923.md`.

D12 implements the next approved exploratory batch: five core predictor comparisons plus two spatial-correspondence controls for each of seeds 42 and 17. It extracts frozen R01/R05 decoder measurements, reuses D11 development and D10M evaluation probability samples, trains small three-outcome heads, and conditionally verifies at most two passing models on complete Val2 images. See `docs/protocols/D12_NIGHT_SEMANTIC_FREQUENCY_20260923.md`.

The code has local CPU numeric tests. Server smoke and execution are pending. Physical GPU0 only; all runtime artifacts under `/home/jovyan/zzx`; Test6 frozen. The script refuses to overwrite existing records and caps wall time at eight hours. The user starts the queue after pulling this branch on the server.

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
conda activate remote_sensing
git pull --ff-only origin rebuild-v1-protocol-20260915
mkdir -p records/rebuild_v1_d12_night_queue_20260923
nohup bash scripts/run_rebuild_v1_d12_night_queue.sh > records/rebuild_v1_d12_night_queue_20260923/launcher.log 2>&1 &
```

Tomorrow, inspect `status.tsv`, `D12_SUMMARY.log`, and `D12_FULL_SUMMARY.log` in the queue directory. `records/rebuild_v1_d12_night_20260923/decision.json` identifies screened candidates and `full_summary.json` records complete-image job coverage. A queue FINISHED line alone does not establish that all stages passed.
