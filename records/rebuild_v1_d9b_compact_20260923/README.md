# D9B user-reported server summary transcription

`user_reported_primary_results.csv` transcribes all 96 score rows printed by
`python -B scripts/summarize_rebuild_v1_d9b_decision_screen.py` in the user's
2026-09-23 server output. The queue status separately reported `QUEUE FINISHED
failures=0`; the Train16 prototype log reported `D9B PROTOTYPES COMPLETE`.
The original server-side `decision_metrics.csv`, prototype JSON, summary JSON,
queue logs, checkpoints and dataset remain under
`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro`. They were not copied
into this repository, so class/size/tile strata and source hashes are not
independently verified by this compact transcription.

All 16 seed-condition groups have six scores. The displayed AUROC/AUPRC are
rounded to four decimals. Treat the 400,000 sampled pixels per group as
correlated observations, not 400,000 independent replicates. No fitted gate,
calibration, routing or held-out test result is present.
