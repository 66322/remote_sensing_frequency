# D18/D19 compact archive — offline audited

`user_reported_decision.json` is an exact JSON extract from the server terminal
output supplied by the user on 2026-09-28. It is a transcript, not an
independently copied or recalculated server artifact. The supplied queue tail
reported `QUEUE FINISHED` at 2026-09-28 12:13:32 +08:00, with 8/8 formal
training/evaluation pairs complete, failures=0, and C4/C5 skipped by the
conditional screen.

The server has now supplied original `status.tsv`, `conditional_gate.json`,
`decision.json`, and all eight formal summaries named `server_*_seed42_summary.json`.
`offline_audit.json` was produced by `scripts/audit_rebuild_v1_d18_d19_archived.py`:
all eight summaries, integer confusion matrices, paired counts, source/config
Git blobs and frozen decision fields passed offline recomputation. The status
file includes one earlier interrupted launch; the audit uses the final run
starting at 2026-09-28 00:18:08 +08:00 from commit `5209403`.

The server checkpoint, dataset and split-file bytes have not been independently
rehashed or re-inferred on this computer. This is still repeatedly used Val2
exploratory evidence, not independent confirmation.

Original server paths:

- `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d18_d19_queue_20260927/`
- `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/rebuild_v1_d18_d19_20260927/`
- `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/runs/rebuild_v1/D18_D19_*`
