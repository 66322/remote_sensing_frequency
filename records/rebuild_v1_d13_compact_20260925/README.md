# D13 compact handoff

`user_reported_stage1_decision.json` transcribes the machine-readable D13
Stage 1 decision pasted by the user. The queue status and summary were also
pasted. The eight `server_<arm>_seed<seed>_summary.json` files are copies
of original server full-image Val2 evaluation summaries, transferred in
commit `8236a07`; they include per-condition, per-tile 6×6 confusion
matrices and class-level harm/rescue counts. Training logs and checkpoints
remain on the server. If the decision transcription differs from an original
summary, the original takes precedence. See
`docs/experiments/D13_RESULTS_20260925.md`.
