# Experiment Result Snapshots

This directory stores frozen, lightweight experiment evidence for Git versioning.

The live training outputs remain under `runs/` and are NOT tracked by Git.

For each important experiment, create one descriptive directory, for example:

- `vaihingen_crossmodal_hf_reliability_rare30/`
- `vaihingen_crossmodal_hf_reliability_rare30_normal_shallow_detail/`
- `vaihingen_crossmodal_hf_reliability_rare30_hf_shallow_detail/`

Recommended files to preserve after an experiment finishes:

- `README.md` — purpose, configuration, result, conclusion
- `metrics_history.csv`
- `best_registry.json`
- selected diagnostic CSV/JSON
- selected per-class evaluation results

Do NOT copy:

- model checkpoints
- resume states
- datasets
- large predictions
- temporary logs

Experiment directory names must explain what the experiment does.
Avoid unexplained names such as P1, P2H, E40, V2, final, new, or latest.
