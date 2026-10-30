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

# Required experiment metadata

Every new experiment record should make it possible to answer:

1. **What question was this experiment designed to answer?**
2. **Exactly which protocol/config/split was used?**
3. **When did the experiment start and finish?**
4. **What result and decision followed?**

For new experiments, record the following fields whenever applicable:

- `experiment_id`
- `purpose`
- `status`: `planned`, `running`, `complete`, `failed`, `aborted`, or `closed`
- `started_at`
- `completed_at`
- `recorded_at`
- `timezone`
- `time_source`
- `git_commit` or source code ref
- `config`
- `dataset_split`
- `seed`
- `checkpoint_selection_rule`
- `test_data_exposure`
- `result_artifacts`
- `decision`

Use ISO-8601 timestamps with an explicit UTC offset, for example:

`2026-09-16T11:19:00+08:00`

For the current training server, records should normally use `UTC+08:00` and may note that the shell displays `CST`.

Do not infer or fabricate missing historical clock times. If only a date is known, keep date precision. If a run is known to have completed only because a later queue or audit observed its summary, write `confirmed complete by <timestamp>` rather than estimating the actual finish time.

For long-running training, the run metadata/summary should eventually retain both `started_at` and `completed_at` automatically so that later analysis does not depend on shell history.

The central REBUILD_V1 timing/status index is:

`docs/experiments/rebuild_v1/INDEX.md`

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

New training scripts should write timing metadata into the run metadata/summary rather than relying only on file or directory names.

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

A date/time suffix may be added when needed to distinguish separate launches, but the authoritative timing should be stored as metadata, not encoded only in the directory name.

---

# Historical experiment mapping

Existing files and run directories are not renamed.

They are mapped to descriptive names in:

docs/START_HERE.md

Git history records code versions.

File names record experiment purpose.

For REBUILD_V1, experiment purpose/status/timing is additionally indexed in:

docs/experiments/rebuild_v1/INDEX.md
