# D9A compact transcription provenance

These files transcribe rounded terminal output supplied by the user. Original
per-condition CSV/JSON outputs and the source SHA256 manifest remain on the
experiment server and take precedence.

In `user_reported_summary_table.csv`, the `dsm_local_down8_q1` rows' **D5 NB
mIoU** and **D5 selected-harm rate** are invalid: the original D9A route
erroneously forced RGB in the locally downsampled quadrant. The expert metrics
and all benefit-ranking values remain unaffected by this routing mask. The
correction uses existing checkpoints with a distinct `fix1` output path;
original files are retained for audit.
