> 历史阶段记录：保留下文当时的判断、建议与条件，不是当前执行指令。研究定位以[研究决策说明](RESEARCH_DECISION.md)为准，待办以[下一步](NEXT_EXPERIMENT.md)为准。特别是外部来源等待、旧seed要求与旧GPU范围不得直接沿用到新任务。

# Conditional follow-up plan — 2026-09-22

Status: B1–B4 complete; no GPU experiment queued. Maintain physical GPU0,
`/home/jovyan/zzx` persistence, failure-continue behavior and historical TEST6
exclusion for any later work.

## P0 — Consolidate the completed evidence

- Treat B4 as partial global replication and failed local mechanism replication.
- Preserve original B1–B4 logs, CSV files, preflight hashes and checkpoints on the
  server; GitHub stores compact evidence and checkpoint references only.
- Use tiles/scenes as evaluation units. Quadrants and pixels are repeated
  measurements, not independent replicates.
- Keep seed42 local results as exploratory rather than averaging away the seed17
  reversal.

## P1 — Low-cost mechanism audit before training

- Measure R01/R05 confidence calibration by condition and class. Raw maximum
  softmax values from independently trained teachers are not automatically
  comparable.
- Quantify how often SafeMaxConfidence chooses each teacher and whether those
  choices improve correctness, separately inside and outside known synthetic masks.
- Separate explicit augmentation masks, exact-zero inference and real metadata
  validity masks. Exact zero-fill recognition is not general missing-data detection.
- Recheck clean, zero, down8 and local results at matched checkpoint steps where
  retained checkpoints permit it, so early checkpoint selection is not confused
  with the teacher mechanism.

These analyses may reuse predictions/checkpoints, but their protocol and output
paths must be reviewed before execution.

## P2 — Requirements for a materially new method

A new training line must isolate:

1. ordinary R05-teacher KD;
2. mask-only supervision using R01 inside known missing masks and fixed R05 outside;
3. confidence-only selection without the synthetic missing mask;
4. the proposed calibrated reliability or explicit Optical-anchor method;
5. matched CE continuation.

The deployable method may use only information available at inference. A synthetic
training mask can supervise learning but cannot be presented as a learned detector
or test-time fallback signal.

## P3 — Independent evidence

- Freeze method, hyperparameters, checkpoint rule and success thresholds before
  viewing new results.
- Use a second Optical/DSM dataset or previously untouched scenes. Audit historical
  exposure before calling any split unseen.
- Add a third random seed only for the selected method and essential controls.
- Include clean, missing, degraded and local failures; report per-class and
  damaged/intact metrics plus efficiency.
- Historical Potsdam TEST6 is exposed and cannot serve as a sealed test.

## Claim boundary

The retained evidence supports the problem statement that DSM is useful under some
degradations yet harmful when absent, and that teacher-target choice can slightly
change global robustness. It does not establish a cross-seed local reliability
mechanism, automatic missing detection, Optical fallback, cross-dataset robustness
or a final publication-ready main method.
