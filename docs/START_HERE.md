# Start Here

**GAMUS Stage A retry prepared.** The first server attempt stopped before
download because `remote_sensing` lacked `h5py`. The updated
[source audit runner](protocols/D20_GAMUS_SOURCE_ACCEPTANCE_20260928.md)
prepares this dependency inside the experiment record and keeps the training
environment unchanged. Pull the new commit, then rerun the CPU audit.

**D20 source priority revised for Stage A, 2026-09-28.** The author-linked
revised [GAMUS source audit](protocols/D20_GAMUS_SOURCE_ACCEPTANCE_20260928.md)
is prepared for a CPU-only server run. Its published files offer RGB, height
and semantic labels from three cities, but rights, content and a geographic
split are unverified. No GPU queue follows automatically. DFC2019 access and
terms remain pending; Vaihingen seed42 remains a failed development screen.

**D20 Vaihingen failure-input audit complete, 2026-09-28.** The 17-tile
CPU-only audit was archived in `21dbb2d`; raw inputs and clean predictions
matched frozen hashes. It found no clear file/label/shape anomaly to explain
tiles 12/14. The [result and evidence limits](experiments/D20_VAIHINGEN_FAILURE_INPUT_AUDIT_RESULTS_20260928.md)
leave the failed gate and no-seed17 decision unchanged. Next resolve US3D
access and usage terms before independent-source training.

**D20 seed42 failure-input audit prepared, awaiting server CPU run.** The
[read-only audit](protocols/D20_VAIHINGEN_FAILURE_INPUT_AUDIT_20260928.md)
checks all 17 development tiles and focuses on 12/14, binding raw input and
clean predictions to the archived hashes. It does not change the failed gate
or start seed17. US3D access and terms remain an independent blocker.

**D20 Vaihingen seed42 development screen completed and failed the frozen
per-tile gate, 2026-09-28.** All three 8,000-step arms and 17-tile/11-condition
evaluations completed; archived-count audit passed. P2 gained +1.0261 pp over
the stronger pooled control but lost on tiles 12 and 14, so seed17 is not
automatically launched. Read the [result and next decision](experiments/D20_VAIHINGEN_SEED42_RESULTS_20260928.md).
US3D independent-source transfer and use terms remain unresolved.

**D20 Vaihingen seed42 queue running as last reported.** The server passed
87 input hashes; P0/P1 each reached 1,000/8,000 training steps. Preserve the
running code/config and archive its decision. A separate
[throughput optimization plan](protocols/D20_THROUGHPUT_OPTIMIZATION_AFTER_SEED42_20260928.md)
covers profiling and matched future versions after this queue finishes.

**D20 Vaihingen seed42 matched development queue prepared, 2026-09-28.**
The fit-only P2 timing probe completed and was archived in `abe10e4`.
The common 8,000-step budget, 17 full development tiles and the gate are frozen in
the [execution protocol](protocols/D20_VAIHINGEN_SEED42_FORMAL_20260928.md).
Server CUDA formal execution is pending. Vaihingen remains same-mosaic development;
US3D independent-source transfer and terms remain unresolved.

**D20 Vaihingen matched one-step smoke passed, 2026-09-28.** P0/P1/P2 each
completed train, save, reload and development-crop evaluation; server evidence
was archived in `8401bcd`. The one-step scores are infrastructure diagnostics.
The next runnable task is the [fit-only timing and memory probe](protocols/D20_VAIHINGEN_FIT_BUDGET_PROBE_20260928.md)
before freezing a common formal training budget. US3D transfer and terms remain
pending for independent geographic confirmation.

**D20 Vaihingen development-source audit completed, 2026-09-28.** All 17
candidate tiles passed sampled content checks, archived in `66ac041`.
Geographic alignment is unverified and the tiles share a mosaic with historical
experiments. Freeze the NIR/red/green input and development split before a
matched P0/P1/P2 smoke. [Read the audit and limitations](current/D20_VAIHINGEN_CONTENT_AUDIT_20260928.md).
The [one-step matched P0/P1/P2 smoke](protocols/D20_VAIHINGEN_MATCHED_SMOKE_20260928.md)
completed on server; it did not launch formal training.

**D20 Stage A server probe completed, 2026-09-28.** Local DFC19 triplets: zero;
official Track-1 torrent metadata reachable; GRSS/DataPort server proxy: 403.
Actual data transfer and terms remain pending. Vaihingen is available for
same-area development, with prior scene exposure and NIR/red/green inputs to account for.
Read the [Stage A result and next action](current/D20_STAGE_A_SOURCE_ACCEPTANCE_20260928.md).
The runnable [Vaihingen content audit](current/D20_VAIHINGEN_CONTENT_AUDIT_20260928.md)
checks the development source while US3D transfer terms are resolved.
The D20 Vaihingen formal development queue is prepared; server execution is pending.

**Latest, 2026-09-28: D18 seed17 replication complete and offline-audited.**
The seed42/17 P0/P1/P2 summaries are archived. P2 passed the prespecified
screen in each seed, with gains of +1.0603/+0.9229 percentage points over
the stronger matched control. Its raw score falls when DSM is fully absent.
Read the [results](experiments/D18_REPLICATION_RESULTS_20260928.md) and
[current handoff](current/HANDOFF.md). The next action is independent-source
feasibility; follow the [D20 staged plan](protocols/D20_INDEPENDENT_SOURCE_AND_MATCHED_BASELINES_20260928.md)
for source acceptance, external matched baselines and a reserved final evaluation region.
No new GPU queue is implemented or scheduled. Val2 remains exploratory and Test6 sealed.

**D18/D19 seed42 completed and archived.** Eight formal
training/evaluation pairs completed with zero failures. Offline audit of the
original summaries passed. P2 passed the within-D18 single-seed screen;
C2/C3 failed and C4/C5 were skipped. P2 is a replication candidate, not a
confirmed method. Read [results](experiments/D18_D19_RESULTS_20260928.md).
Do not relaunch the seed42 queue.

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
