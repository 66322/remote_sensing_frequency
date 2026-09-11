# Experiment Naming Convention

## Principle

Experiment names must explain what the experiment does.

Do not use unexplained version labels as the primary name:

- P1
- P2H
- E40
- V2
- V3
- V4
- final
- new
- latest

Historical files are kept unchanged.

This naming convention applies to new experiments.

---

# Experiment slug

Format:

<dataset>_<core_method>_<sampling>_<new_component>

Examples:

vaihingen_crossmodal_hf_reliability_rare30

vaihingen_crossmodal_hf_reliability_rare30_normal_shallow_detail

vaihingen_crossmodal_hf_reliability_rare30_hf_shallow_detail

vaihingen_dsm_hf_calibration_rare30

vaihingen_history_hard_region_sampling30

---

# Model files

The model filename describes only model structure.

Examples:

model/crossmodal_hf_reliability.py

model/crossmodal_hf_reliability_shallow_detail.py

Sampling strategies such as Rare30 should not appear in model filenames
unless they actually change the network structure.

---

# Training scripts

Format:

scripts/train_<dataset>_<full_experiment_description>.py

Examples:

scripts/train_vaihingen_crossmodal_hf_reliability_rare30.py

scripts/train_vaihingen_crossmodal_hf_reliability_rare30_normal_shallow_detail.py

scripts/train_vaihingen_crossmodal_hf_reliability_rare30_hf_shallow_detail.py

---

# Analysis scripts

Format:

scripts/analyze_<experiment_or_comparison>_<purpose>.py

Example:

scripts/analyze_vaihingen_shallow_detail_per_class.py

---

# Run directories

Format:

runs/<experiment_slug>/seed<seed>_<budget>/

Example:

runs/vaihingen_crossmodal_hf_reliability_rare30_normal_shallow_detail/seed42_10k/

---

# Historical experiment mapping

Existing files and run directories are not renamed.

They are mapped to descriptive names in:

docs/EXPERIMENT_MASTER.md

Git history records code versions.

File names record experiment purpose.
