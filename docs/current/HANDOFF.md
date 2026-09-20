# Current handoff — 2026-09-20

## Branch and execution snapshot

- Research branch: `rebuild-v1-protocol-20260915`; GitHub default: `main`.
- Link for a new conversation: https://github.com/66322/remote_sensing_frequency/tree/rebuild-v1-protocol-20260915
- B1 launch code: `e2ad594049f36c118b31d659335715b089e1fe0b`,
  committed 2026-09-20 12:56:50 +08:00.
- User's latest status: experiments still running, no conclusion.
- Latest detailed pasted log: B1-C step 1980/4000, approximately 1.82–1.92
  seconds/step. Observation timestamp unknown; do not project this as live status.
- Fix2 queue started 12:57:56; B1-C smoke completed 13:01:23;
  B1-C formal stage started 13:01:26 (+08:00).
- Smoke completed 20 steps with clean NB mIoU 87.09330223522393%;
  this is an engineering check, not a formal result.
- Current queue: `records/rebuild_v1_b1_pilot_queue_fix2_20260920`.
- Launcher: `records/rebuild_v1_b1_pilot_queue_fix2_20260920_launcher.log`.
- Final summary, when available:
  `records/rebuild_v1_b1_pilot_summary_20260920/decision_evidence.json`.
- No server connection was available for this audit; observations come from
  user-provided logs and are not live monitoring.

The current audit changes documentation and evidence provenance only. Do not
pull or restart a running queue merely because handoff documents were updated.

## Non-negotiable constraints

Only physical GPU 0, with `CUDA_VISIBLE_DEVICES=0`. Server root:
`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro`.
Persistent server outputs must stay in `/home/jovyan/zzx`, with run outputs
in project `runs/` and compact evidence in `records/`.
Raw datasets and pretrained assets are read-only. Failed experiments move on;
do not retry automatically. Do not upload datasets or model weights.

Historical TEST6 is exposed development evidence and is prohibited in current
training/selection/evaluation. It cannot be relabelled as an untouched final test.

## What a new conversation can rely on

1. Core seed42 R01–R05/C-OO/C-OO-QD compact metrics and reports are committed.
2. Follow-up A1/A2, seed17, D1–D6 were reported complete by the user. Their
   conclusions in PROJECT_STATUS are provisional pending compact-artifact archival.
3. `records/rebuild_v1_handoff_20260920/user_reported_snapshot.json` preserves
   selected supplied values with explicit provenance. It is not a reconstructed
   original evaluation file, and must not be used to fabricate missing rows.
4. B1 has no final result or publication claim. KD/SAFE completion is unknown.
5. Missing original files mean archival is needed, not that the experiment
   should be repeated.

Read `EVIDENCE_AUDIT_20260920.md` and `FOLLOWUP_PLAN.md` before making decisions.
D4's historical rejected proposal called “B1 frozen-expert gate” is distinct
from today's B1 distillation pilot.

## First action after receiving new server results

Read queue status and each arm's trainer summary, validation history, checkpoint
reference and robust metrics. QUEUE FINISHED only means the script reached its
end; individual stages may have FAILED/SKIPPED. Check completed step=4000 and
TEST6 flags, then compare C, KD and SAFE. A missing arm is not a negative result.
Do not automatically start a full 16k continuation from the summary Boolean.

For publication, archive actual compact outputs and their SHA256 manifests,
update result provenance, and freeze the selected method and evaluation
protocol before independent validation. GitHub cannot report live GPU progress.

## Reusable new-conversation request

“Read this rebuild branch's docs/START_HERE.md and docs/current/HANDOFF.md first.
Continue from the last observed state without repeating completed experiments.
B1 was running at handoff and has no final conclusion; check fresh supplied
status before scheduling anything. Use GPU 0 only, keep all server outputs under
zzx, and move on after a failed experiment. Distinguish committed original
metrics from user-reported summaries.”
