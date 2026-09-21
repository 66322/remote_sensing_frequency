# Current handoff — 2026-09-21

## Read this first on another computer

- Branch: `rebuild-v1-protocol-20260915`
- Repository: https://github.com/66322/remote_sensing_frequency/tree/rebuild-v1-protocol-20260915
- Current completed evidence: `records/rebuild_v1_b2_b3_compact_20260921/`
- Interpretation and thesis boundary: `docs/experiments/B2_B3_RESULTS_20260921.md`
- Current experiment: B4 seed17 replication; do not restart it based only on this handoff.

GitHub preserves the committed compact data, code, decisions and server-path index across computers. It does not contain the large checkpoints or automatically read future server outputs. Those remain under `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro`. After B4 finishes, supply the final launcher/summary output to Codex and commit a new compact result package before changing the active machine if possible.

## Completed state

B1/B2/B3 are complete as reported by the user. The seed42 headline is:

- KD minus C: +0.2247 pp clean, +0.5275 pp DSM down8, +0.6918 pp DSM zero.
- R05_KD minus KD: +0.2217 pp clean, -0.2220 pp DSM down8, -0.1568 pp DSM zero.
- SAFE minus KD: +0.0775 pp clean, +0.1627 pp down8, -0.1679 pp zero; no consistent extra benefit.
- In B3 paired local evaluation, KD degrades less than R05_KD in all eight tile x family x region comparisons.
- KD versus CE is mixed on local missing boundaries; do not claim complete missing-modality robustness.

The compact files are transcriptions of user-supplied terminal output. Original server artifacts take precedence and should be archived later with hashes when convenient; missing GitHub copies are not a reason to rerun completed experiments.

## Running state

Last observed at 2026-09-21 17:25:17 +08:00:

- B4 queue started at 17:22:07.
- `C17_SMOKE` completed successfully at 17:25:15.
- `C17_TRAIN` started at 17:25:17.
- Physical GPU: 0, NVIDIA H100 80GB HBM3; logical device `cuda:0`.
- Queue root: `records/rebuild_v1_b4_seed17_20260921/`.
- Launcher log: `records/rebuild_v1_b4_seed17_20260921_launcher.log`.
- PID file: `records/rebuild_v1_b4_seed17_20260921.pid`.
- Planning ETA: 2026-09-22 01:20–02:20 +08:00; hard 12-hour limit near 05:22.

This is not live status. A new session must inspect fresh output supplied by the user.

## B4 scientific gate

B4 compares only C17, R05_KD17 and KD17 under a matched seed17 protocol:

1. C17 controls for continued CE training.
2. R05_KD17 measures generic distillation from the dual-modal R05 teacher.
3. KD17 measures the additional effect of SafeMaxConfidence teacher-target selection.

The primary decision uses clean/down8/zero global metrics and paired local damaged-region changes. Boundary and per-class scores are diagnostic. If KD17 retains the DSM-degradation advantage over R05_KD17, the reliability-teacher mechanism can enter the main thesis result. If the direction reverses, seed42 must be reported as exploratory.

## Required completion check

Do not infer completion from elapsed time. Confirm:

1. launcher reports success for each intended stage rather than FAILED/SKIPPED;
2. each trained arm reached expected step 4000;
3. `test6_loaded` is false;
4. robust and paired summary files exist for C17, R05_KD17 and KD17;
5. final markers include `B4_SEED17_SUMMARY_COMPLETE`, `SUMMARIZE COMPLETE` and `QUEUE COMPLETE`.

Then commit aggregate CSV/JSON, configuration/checkpoint identity, timestamps, conclusion, original server paths and hashes where available. Do not commit weights, datasets or large prediction arrays.

## Non-negotiable execution constraints

Use physical GPU 0 only with `CUDA_VISIBLE_DEVICES=0`. Keep persistent outputs under `/home/jovyan/zzx`. Historical TEST6 is prohibited. Raw datasets and pretrained assets are read-only. Failed experiments move on and are not automatically retried.

## Reusable prompt on the second computer

“Read `docs/START_HERE.md`, `docs/current/HANDOFF.md`, and `docs/experiments/B2_B3_RESULTS_20260921.md` on branch `rebuild-v1-protocol-20260915`. B1/B2/B3 are complete; B4 seed17 was last observed running on GPU 0. Do not repeat completed experiments. I will paste the fresh B4 launcher and summary output; verify completion, extract compact metrics, update the registry/status/handoff, and commit the result package to GitHub.”
