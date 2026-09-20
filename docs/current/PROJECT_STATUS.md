# Current Project Status

- Updated: 2026-09-20
- Active branch: `rebuild-v1-protocol-20260915`
- Current line: REBUILD_V1 multimodal capacity and robustness audit
- Dataset: ISPRS Potsdam
- Development split: Train16 / Val2
- Val2 tiles: `3_11`, `5_10`
- Historical TEST6: prohibited for training, checkpoint selection and current diagnostics
- Formal seed: 42
- Formal schedule: 16000 optimizer steps
- Selection metric: Val2 NoBoundary mIoU_fg5

Evidence status: core seed42 compact records are committed. Follow-up results
below are user-reported server outputs; original D1-D6 records await archival.
See `HANDOFF.md` and `EVIDENCE_AUDIT_20260920.md`. B1 is running as last
reported on 2026-09-20, with no final result in GitHub. Its 4k is additional
training from the R05 checkpoint, not a replacement for base training.

## Completed core results

| ID | Meaning | FullGT mIoU_fg5 | NB mIoU_fg5 | Status |
|---|---|---:|---:|---|
| R01 | true Optical-only | 80.6883 | 85.3713 | complete |
| R02 | clean Optical+DSM | 81.8483 | 86.2016 | complete |
| R03 | quality-corruption training Q | 82.1069 | 86.5251 | complete |
| R04 | modality-dropout training D | 81.6042 | 85.9818 | complete |
| C-OO | Optical+Optical capacity control | 81.8281 | 86.3548 | complete |
| R05 | Optical+DSM with Q+D | 82.5147 | 87.0485 | complete |
| C-OO-QD | Optical+Optical with matched Q+D | 81.6670 | 86.1969 | complete |

These are seed42 results on the two-tile Val2 development split. They are not
multi-seed or held-out test conclusions.

## Completed follow-up results

| ID | Clean NB mIoU_fg5 | DSM-zero | DSM-down8 | Decision |
|---|---:|---:|---:|---|
| A1 no Optical dropout | 86.4066 | 81.2529 | 85.7454 | negative fallback ablation |
| A2 DSM dropout 20% | 85.7936 | 83.9292 | 84.8006 | fallback/clean tradeoff |
| R05 seed17 | 85.8600 | 83.2120 | 84.4839 | replication complete |
| C-OO-QD seed17 | 85.6440 | 83.0267 | 77.8835 | replication complete |

R01 seed17 reaches 85.8366 clean NB mIoU_fg5. R05 therefore exceeds R01 by
only 0.0234 pp on clean seed17, while its down8 advantage over C-OO-QD remains
large at 6.6004 pp.

## Current evidence

- R05 exceeds matched C-OO-QD by about 0.8517 pp NB mIoU_fg5 on clean Val2.
- R05 remains stronger under second-stream blur/down2/down4/down8.
- Under down8, R05 exceeds the matched C-OO-QD condition by about 6.1502 pp.
- With DSM completely zeroed, R05 reaches 83.1294 NB mIoU_fg5, below R01 at 85.3713.
- C-OO clean exceeds R02 clean, so the entire R02-R01 difference cannot be
  attributed to DSM-specific information.
- Optical-zero is not an equivalent semantic comparison between R05 and
  C-OO-QD and must not be used as direct DSM-value evidence.

## Current conclusion boundary

Supported:

- Q+D is a strong robustness baseline.
- DSM provides condition-dependent value beyond a matched second-stream
  capacity control under several degradation conditions.
- A fallback gap remains under complete DSM absence.

Not supported:

- DSM is beneficial under every condition.
- A new frequency module has beaten simple robust training.
- The current single-seed two-tile evidence is a final test-set conclusion.

## Local diagnostics

- R05 local-down8 advantage over C-OO-QD averages 2.4555 pp across whole tiles.
- Inside damaged local-down8 regions, R05 exceeds C-OO-QD by about 7.0087 pp.
- Inside local missing regions, R05 does not exceed C-OO-QD.
- Shift loss is monotonic in all directions, but averages only 0.2340 pp across
  all tested offsets.

## Active work

The active experiment is the B1 single-student distillation pilot. D5 identified
SafeMaxConfidence as the only shared passing nonlearned router across seeds 42
and 17 under an asymmetric candidate set: other fusion rules were not supplied
the same hard fallback. D6 explicit/inferred-zero scores agree to four printed
decimals, but supplied full-precision rows contain tiny differences. Neither
mask equality nor general missing-data detection was established. The missing
family mean exceeds the larger of the two expert family means by
1.2121/0.4430 pp; this is not the mean gain over each condition's best expert.
The router requires both R01 and R05 at inference.

B1 compares a matched 4k CE continuation, safe-teacher distillation, and
safe-teacher distillation with an extra R01 constraint on missing pixels. The
goal is to retain the safe router's fallback behavior in one R05-structure
student before considering a new fusion architecture.

B1-SAFE adds weight to a missing-region R01 KL target already present in
B1-KD; it provides no guaranteed Optical-only path. The student retains the
dual-input, dual-branch F0 architecture. The latest supplied detailed log reached
B1-C step 1980/4000, without an observation timestamp; this is not live progress.
