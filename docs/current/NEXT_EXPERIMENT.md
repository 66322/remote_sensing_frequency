# Next decision after D10M - 2026-09-23

D10M reported complete: 20/20, zero failures. The result is extracted and
recorded in `docs/experiments/D10M_RESULTS_20260923.md`. No more data or
result audits are required to make the primary decision.

## Close the tested feature branch

Structure_r8 has 2 wins / 34 losses on available-DSM comparisons. After
removing the matched edge-shift duplicates: 1 win / 23 losses. The small
positive is +0.0030 pp. Circular shifts preserve amplitude but their mIoU
effect has opposite directions across expert seeds. Close this fixed-score
hypothesis; no more radius, threshold or weighted-sum optimization on Val2.
Do not start residual-gate training. Keep D9A/D9B/B1-B4 closed as well.

## Next model work, not another source inventory

Negative-transfer suppression remains the research objective. The next
possible experiment is a separately preregistered, small supervised
benefit/harm predictor, starting with expert-output-only inputs. Establish
learnability before assuming semantic or frequency descriptors help. Then
compare capacity-matched semantic-only, frequency-only, semantic+expert,
and full models. Retain calibrated confidence/entropy and expert disagreement
controls. Semantic and frequency are candidate inputs, not proven reliability.

This is a new hypothesis, not a positive D10M gate decision. Freeze actual
head-fit, calibration and evaluation scene groups before implementation.
A local exploratory experiment may use available development data, with
explicit expert-training exposure disclosure; it cannot be called independent
confirmation. Do not train or calibrate on Val2 and report the same pixels
as held-out evidence. Do not random-split pixels across adjacent scenes.

No learned-model queue is implemented or launched in this result-recording
update. No DFC19 download or metadata inventory is a prerequisite for the
next protocol. Existing D10M caches are preserved; they are diagnostic
Val2 data and not an independently held-out fitting dataset.

Only genuinely incremental, cross-seed evidence can reopen the residual-gate
entry criterion. Calibrated benefit probabilities, held-out corruption
families, RGB failure and independent confirmation remain required before
strong final claims. Physical GPU 0, writes under /home/jovyan/zzx, failures
continue, Test6 frozen. No new shell command is required for this closed batch.
