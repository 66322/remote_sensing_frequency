# D14 compact user-output transcription

`user_reported_intervention_summary.csv` contains the exact 16 Python-dict
rows printed in the user's pasted `D14_SUMMARY.log`. The pasted queue status
reports 8/8 full-image evaluations complete, no missing rows, and zero
failures, ending 2026-09-26 00:26:16 +08:00 at commit `877e39c`.

The eight `server_<arm>_seed<seed>_summary.json` files are copies of the
original server full-image evaluation outputs, transferred in commit
`348dda6`. They contain per-condition, per-tile/class matrices, harm,
rescue and prediction-flip counts. The source-file audit found no
discrepancy against the transcription. Logs remain under
`records/rebuild_v1_d14_dsm_intervention_20260926/` on the server.
See `docs/experiments/D14_RESULTS_20260926.md`.
