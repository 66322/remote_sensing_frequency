# E51-B same-step metadata correction

Date: 2026-09-15

This note corrects stale labels in the historical same-step PP/PH output metadata. It does not change any numerical result.

Authoritative interpretation:

- PP checkpoint: 4k.
- PH checkpoint: 4k.
- Comparison: strict same-step PP4k vs PH4k.

Known stale labels:

1. `summary.json` -> `comparison_note` says PP10k vs PH4k, but the result keys and checkpoint steps are PP4k/PH4k.
2. `pp_vs_ph_relative_robustness.csv` uses column names `PP10k_nb_mIoU` and `PP10k_drop_pp`; those columns contain PP4k values in this directory.
3. The generator `scripts/eval_e51b_same_step_pp4k_ph4k.py` contains the same stale text/column names.

Until the historical JSON/CSV is regenerated or safely patched, use the checkpoint-step fields and PP4k/PH4k result keys as authoritative.

No metric value is altered by this correction note.
