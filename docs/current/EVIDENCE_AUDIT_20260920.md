# Evidence and handoff audit — 2026-09-20

## Scope and provenance

Audited remote research HEAD before this documentation update: `e2ad594`.
Git fetch confirmed the midday B1 additions and both fixes are on GitHub.
The GitHub default branch remains main. This audit does not verify live server
state or claim any B1 result.

| Evidence group | Available in GitHub at audit | Gap |
|---|---|---|
| Core seed42 baseline matrix | configs, trainers, compact metrics and reports | development Val2 only |
| A1/A2 and seed17 follow-ups | scripts/configs, narrative metrics | original summaries, curves, references and evaluations not archived |
| D1–D3 | scripts and narrative findings | original dataset/region/per-class metrics absent |
| D4/D5 | scripts and user-reported decision values | original per-seed CSV and decision JSON absent |
| D6 | scripts and user-reported rounded table / selected raw rows | per-seed method_metrics.csv, timings.csv, summary.json absent |
| B1 | corrected code/configs and reported smoke/training progress | running; complete training/robustness outputs unavailable |

The handoff snapshot preserves selected user-reported data separately. No absent
evaluation directory is manufactured. The registry's expected_server_records
are destinations to collect, not evidence already committed.

## Corrected stale or unsupported statements

- README and index incorrectly named D1–D3 as pending; they now distinguish
  reported completion from archived originals.
- B1 was “planned/server execution pending”; it is now running as last reported.
- Registry last_updated remained September 18; it is now September 20.
- D1–D3 summary path was wrong: the implemented writer uses
  `records/rebuild_v1_local_failure_comparison_20260918/`.
- D6 has no combined summary writer in this queue; its real outputs are the
  two per-seed directories, not a claimed combined summary directory.
- D6 inferred/explicit scores are close, not exactly identical. For seed42,
  missing_rect_10pct NB, supplied fractions were 0.8703313848065374 versus
  0.8703314031268482. This says nothing about exact mask equality.
- “Best expert” family gain was safe family mean minus max(expert family means).
  It is not the average of per-condition best-expert gains.
- D4's old B1 gate proposal and today's B1 distillation have different meanings.

## Methodological limitations

1. D5 hard missing-region fallback was only applied to max-confidence routing.
   Safe average/fixed-weight/entropy controls remain necessary.
2. Missing-region targets in B1-KD already use R01. B1-SAFE increases weight
   on that same KL target; it does not create a guaranteed fallback path.
3. The student is one dual-input F0 model, not an Optical-only network.
   Base R05 training, continuation and teacher costs must be reported separately.
4. The B1 summary compares SAFE to C only, and thresholds are exploratory
   tolerances. It cannot establish superiority over KD, significance, a safety
   guarantee or readiness for longer training. Preserve original thresholds;
   document supplementary analysis separately.
5. B1 chooses checkpoints on clean Val2. Report that selection rule and final
   checkpoint results if later evaluating trade-offs; do not retrospectively
   pick a different checkpoint per failure condition.
6. B1 trains on rectangular missing/blur/downsampling treatments. Same-type
   test results are robustness evidence, not unseen-corruption generalization.
7. D6 measures whole-image scores; damaged/intact/boundary regions are needed
   for local claims. Different masks on two tiles are not independent datasets.
8. DSM==0 detects a chosen fill convention; normalized valid DSM can be zero.
   NoData-mask quality and naturally missing/degraded DSM remain unverified.
9. Confidence is not automatically calibrated across separately trained
   experts. Routing benefit must be compared to simpler matched rules.
10. Repeated Val2 selection (two tiles) and exposed TEST6 prevent claims of
    untouched-test generalization. Seeds do not replace independent spatial
    data. Do not treat overlapping crops/pixels as independent statistical units.

## Engineering issues to respect while the queue runs

- QUEUE FINISHED 0 is unconditional; examine all per-stage return codes.
- Boundary-preflight failure can return before a stage START/FAILED row;
  inspect queue.log when a stage is absent.
- Output names are fixed and trainers refuse existing run directories.
  Starting a queue again is not an automatic resume operation.
- B1 resume signature omits some config fields; do not edit config and resume
  as if it were the same experiment. Historical R02 resume validation does not
  by itself validate every newer trainer.
- The generic robust evaluator is invoked with variant R05 even for B1;
  distinguish arms by run directory/config/checkpoint, not variant alone.
- Paths and run-state safeguards should be tightened in a later version,
  without modifying the in-flight pilot.

## Required archival before publication

For A1/A2 and seed17: actual trainer summaries, run metadata, validation
histories, augmentation counts, checkpoint path/size/SHA256, and robust metrics.
Use the existing next-queue archival script only after checking completed inputs.

For D1–D6: copy original compact CSV/JSON, exact configs/code commit, per-seed
timing/region records where generated, and frozen queue statuses. Do not invent
region/per-tile outputs that the script never generated.

For B1 after completion: status and failures, all three trainer summaries and
curves, best-checkpoint step and SHA256 references, FullGT and NoBoundary
per-condition/per-class/per-tile metrics, and the original decision JSON.
Record incomplete stages explicitly. Weights remain on the server.

Repository handoff readiness after this documentation update: sufficient for
context and safe continuation, not a complete independent reproduction or
publication evidence package.
