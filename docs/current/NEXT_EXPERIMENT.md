# Next experiment: D12 night batch

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
