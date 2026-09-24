# Next research decision after D12 (2026-09-24)

**2026-09-24 direction proposal:** After reviewing D9-D12, the next concrete
method question is a staged RGB-anchored DSM residual training pilot, specified
in `docs/protocols/D13_RGB_ANCHORED_DSM_RESIDUAL_PILOT_20260924.md`.
Stage 1 compares matched RGB-capacity, DSM-CE, and DSM-risk arms in both seeds;
semantic/frequency ablations are conditional on Stage 1. This is a design
proposal, not implemented code or authorization to launch a queue. It is a
new training mechanism, distinct from the failed D12 frozen-expert selector.
Potsdam Val2 can give exploratory development evidence only; an independent
scene source is still required for final confirmation. Do not use Test6.

D12 completed 14/14 heads with zero queue failures and **no candidate** under
the prespecified two-seed gain/harm screen. Complete-image confirmation was
correctly skipped. The exact server-output transcription and interpretation
are in `docs/experiments/D12_RESULTS_20260924.md`. Do not relaunch D12 or
relax its Val2 thresholds after seeing the result.

The next step is a bounded decision memo using D9–D12 evidence: decide whether
a benefit-aware selector warrants a new experimental design. A new fitted
method needs a genuinely changed mechanism or supervision target and a frozen,
spatially independent labelled evaluation source. The repeatedly inspected
Val2 cannot serve as confirmation. Keep the question of DSM's marginal
decision value over RGB, but do not claim that this semantic/frequency head
solves it. Do not start residual-gate training, Test6 evaluation, or another
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
