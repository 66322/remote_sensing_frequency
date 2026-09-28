# Start Here

**Latest, 2026-09-28: D18/D19 seed42 complete and archived.** Eight formal
training/evaluation pairs completed with zero failures. Offline audit of the
original summaries passed. P2 passed the within-D18 single-seed screen;
C2/C3 failed and C4/C5 were skipped. P2 is a replication candidate, not a
confirmed method. Read [results](experiments/D18_D19_RESULTS_20260928.md) and
[current handoff](current/HANDOFF.md). The next proposed batch is matched
P0/P1/P2 seed17; its code and queue are not yet implemented. Do not relaunch
the seed42 queue.

**Historical launch note, 2026-09-27:** Follow the
[single-seed execution instructions](protocols/D18_D19_EXECUTION_20260927.md):
8 base runs plus at most2 conditional runs, GPU0/1, integrated evaluation, no seed17.
Server smoke/launch still pending. D16/D17 completed, archived and audited; both candidate gates failed.
Do not relaunch that queue. Read [current handoff](current/HANDOFF.md) for the immediate action.

**Historical material follows.** Earlier running/repair/launch notes are superseded by the current handoff.

**D16/D17 launch repair:** User's server queue stopped at15:29:20 +08:00 on
2026-09-26: eight smokes failed at CUDA cross_entropy NLL2d under strict
determinism. Formal pilots never started. Equivalent CE implementation and
regression checks are added; pull and relaunch the same D16/D17 command below.

**Next design, 2026-09-26:** Read the [post-D15 portfolio](protocols/D16_D17_RESEARCH_PORTFOLIO_20260926.md).
It proposes sixteen matched continuation pilots covering task-conditioned
intervention learning and geometry supervision, with pretrained adaptation as
a reserved alternative. RGB-DSM reliable segmentation remains the topic;
down4 is one stress condition. The training/evaluation/shared two-GPU queue is
now implemented and locally checked; server CUDA smoke/launch not yet observed.
Use the server commands in that protocol. Do not relaunch the completed D15 queue.

**D15 complete and offline-audited, 2026-09-26:** Last user-reported server
completion is 14:45:11 +08:00, eight evaluations complete, both workers0.
The prespecified RGB degradation screen passed in both seeds. Read
[`D15 results`](experiments/D15_RESULTS_20260926.md): down4 gains are positive
in both seeds and both tiles, while mild-condition gains vary by tile. These
findings motivate the two hypotheses above, not a demonstrated restoration
method. Do not rerun completed D15.

**D15 evaluation repair pending server replay:** Both DSM-only 16k trainings
completed, but evaluation failed exact clean confusion-matrix reproduction at
05:49:46 +08:00 on 2026-09-26. The evaluator now uses the deterministic runtime
settings from training validation and saves matrix differences if reproduction
still fails. Pull and relaunch the same queue to reuse trained checkpoints;
do not retrain or treat this as a research result.

**D15 queue repair, 2026-09-26:** The user's server log showed both smokes
complete at 01:18:08 +08:00, then `worker0=1 worker1=1` before formal training.
The shell worker had an unbound local variable under `set -u`; this is fixed
and regression-tested. Pull the latest branch and relaunch the same command in
the [D15 protocol](protocols/D15_DSM_CAPABILITY_RGB_DEGRADATION_20260926.md).
Existing smoke summaries are reused. GPU0 and GPU1 remain authorized; Test6
stays frozen.

**Latest observed result (2026-09-26 00:26:16 +08:00):** D14 completed
8/8 full-image evaluations with zero queue failures. The DSM heads change
predictions when DSM content changes while availability remains true;
the matched RGB controls do not change. This is a sensitivity diagnostic,
not a benefit result. The eight original summaries were transferred in
commit `348dda6` and audited. Read
`docs/experiments/D14_RESULTS_20260926.md`.
Do not rerun it. Read `docs/current/NEXT_EXPERIMENT.md` for the next
research decision; there is no active GPU queue.

**Current decision (2026-09-25):** D13 Stage 1 finished all eight matched
train/evaluation pairs with zero queue failures, but failed its prespecified
two-seed gate; conditional Stage 2 was skipped. Read
`docs/experiments/D13_RESULTS_20260925.md` and the top of
`docs/current/NEXT_EXPERIMENT.md`. The older D13 launch instruction below is
historical; do not relaunch it. The eight original evaluation summaries
reached GitHub on 2026-09-26 and support the paired diagnostic in the report.

**Latest preparation (2026-09-24):** D13 residual training and evaluation code
is prepared on this branch, with an unattended 24-hour queue. Server smoke and
formal GPU work have not yet run. Read
`docs/protocols/D13_RGB_ANCHORED_DSM_RESIDUAL_PILOT_20260924.md` and the top
of `docs/current/NEXT_EXPERIMENT.md`. D12 remains a failed exploratory screen.
The D13 queue is a new training mechanism and Val2 is development evidence.

**Active next action (2026-09-24):** D12 completed 14/14 without a screened
candidate. Read `docs/experiments/D12_RESULTS_20260924.md` and
`docs/current/NEXT_EXPERIMENT.md`. Do not rerun D11/D12 or train a safety gate
from their failed screens. Historical instructions below are superseded.

**Historical next action:** execute the implemented D11 supervised benefit probe
queue. Read `docs/current/NEXT_EXPERIMENT.md` and
`docs/protocols/D11_SUPERVISED_BENEFIT_PROBE.md`. Server results pending.
The D10M closure below still applies to its fixed-score mechanism branch;
D11 is a new supervised head experiment with off-Val2 fit/calibration.

Latest decision (2026-09-23 17:50:39+08:00 server completion): D10M
reported 20/20, zero failures. Its fixed structure score fails the criterion;
close the mechanism branch. Do not execute older run instructions below.
See `docs/experiments/D10M_RESULTS_20260923.md` and `NEXT_EXPERIMENT.md`
(in docs/current). No additional audit or residual-gate queue is requested.

This is the mandatory entry point for every new conversation, computer and
experiment.

Research branch: `rebuild-v1-protocol-20260915`; GitHub defaults to `main`.

D9B's unfitted Val2 decision-benefit screen has now completed and failed its
cross-seed entry gate; see `docs/experiments/D9B_RESULTS_20260923.md`.
Do not launch a safety-gate fit from those features. The next source decision
is described at the top of `docs/current/NEXT_EXPERIMENT.md`.
The original-versus-current direction check is in
`docs/current/DIRECTION_CHECK_20260923.md`.
The independent dataset decision is in
`docs/current/INDEPENDENT_SOURCE_DECISION_20260923.md`.
The conditional D10 method design is in
`docs/protocols/D10_SELECTIVE_DSM_BENEFIT.md`; it is not yet a GPU queue.
Read `docs/current/HANDOFF.md` first for the current evidence and decision boundary.
As of 2026-09-23, B1–B4, D7, D8 and D9A are complete. B4 fails its local
replication gate; D8 fails its sampling gate. D9A's simple disagreement
interaction loses to confidence on all reported benefit-ranking comparisons.
Entropy difference ranks benefit above confidence in all 16 comparisons, but
the subsequent matched safe-entropy router loses mean mIoU to safe confidence.
The D5 per-seed result directories were absent in the latest server check,
although its logs report completion. A matched safe-entropy routing decision
audit completed as an exploratory D9A follow-up. The original D9A
local-down8 D5 route incorrectly forced RGB in degraded but available DSM;
its two-seed `fix1` correction completed with zero failures. The entropy-route
queue finished with zero failures: safe entropy won routed mIoU in only 4/16
rows, lost in 10 and tied under DSM zero (mean -0.0089 pp). The full D9 gate
remains unevaluated; a fitted D9B needs an independent evaluation source.
The D9A class/region review is complete and closed. The next screen is
decision-relevant DSM benefit on expert-disagreement pixels; see
`docs/protocols/D9B_DECISION_BENEFIT_SCREEN.md`.
The documented Potsdam and Vaihingen scenes
are already exposed; see `docs/current/D9B_SOURCE_STATUS_20260923.md` before
proposing a new source.
Do not rerun unchanged SafeMaxConfidence distillation or the conditional D8
seed17 arm from a stale conversation snapshot.

## Mandatory execution rules

These rules apply to every training run, evaluation, diagnostic and queue.

1. Use only the physical GPU indices authorized in the active experiment protocol.
   D18/D19 permits physical GPU 0 and GPU 1 as independent queue workers.
2. Set `CUDA_VISIBLE_DEVICES` to the worker's assigned physical index before
   Python starts; inside that process use logical device `cuda:0`.
3. Distributed execution, `torchrun` and fallback to another GPU are forbidden.
4. All persistent files must remain under `/home/jovyan/zzx`.
5. Project code and outputs must remain under
   `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro`.
6. Runtime outputs go to project `runs/`; compact evidence goes to `records/`.
7. Raw datasets and pretrained weights are read-only.
8. Do not upload checkpoints, training states, datasets or complete `runs/`
   directories to GitHub.
9. Apply the active queue's preflight. The GPU0-only
    `scripts/validate_execution_boundaries.py` is for historical GPU0 queues;
    D18/D19 performs its own dual-worker preflight.
10. Before proposing a new experiment, check `DO_NOT_REPEAT.md` and the JSON
    experiment registry.
11. If a requested command conflicts with these rules, stop instead of
    silently changing the GPU or output path.

Full policy:

`docs/protocols/EXECUTION_BOUNDARIES.md`

Machine-readable policy:

`configs/execution_boundaries.json`

## Required reading order

1. This file and its mandatory rules.
2. `docs/protocols/EXECUTION_BOUNDARIES.md`
3. `docs/current/PROJECT_STATUS.md`
4. `docs/current/DO_NOT_REPEAT.md`
5. `docs/current/NEXT_EXPERIMENT.md`
6. `docs/experiments/rebuild_v1/INDEX.md`
7. `records/rebuild_v1_experiment_registry.json`
8. `docs/protocols/NAMING_CONVENTION.md`
9. `docs/current/EVIDENCE_AUDIT_20260920.md`
10. `docs/current/FOLLOWUP_PLAN.md` (conditional proposals, not queued work).

Files under `docs/archive/` are historical evidence only. They must not be used
to determine current status or the next experiment.

## Experiment closure rule

After every formal experiment:

1. verify completion and TEST6 isolation;
2. archive the decision, every arm's compact evaluation summary and the queue
   status in GitHub, including failures and skipped arms;
3. analyze the archived results and write an experiment report with the exact
   comparisons, gate decisions, limitations and next action;
4. update the registry, status, do-not-repeat list, experiment index and next
   experiment;
5. generate an artifact SHA256 manifest;
6. commit code, configuration, results, analysis and documentation together;
7. push and verify that local and remote commits match.

The minimum evidence needed for another computer to judge the experiment is
specified in `docs/protocols/EXPERIMENT_GITHUB_HANDOFF.md`. Server paths and
hashes alone do not close an experiment.
