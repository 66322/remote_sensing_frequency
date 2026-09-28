# D18 matched seed17 replication results (2026-09-28)

Status: **COMPLETE**. Executed commit: `b66a9017129b0d6adc45c71cc6e9ca042548fc0b`.
This is exploratory Val2 evidence; Test6 remains sealed. Train16 has 16 tiles and Val2 has two.
P0 is RGB, P1 is RGB plus RGB-derived gray, P2 is RGB plus DSM. All use the same frozen DINO backbone and 8000 steps.

## Score and prespecified decision

| Training seed | Arm | Macro mIoU_fg5 (%) | Clean (%) | RGB quality (%) | Auxiliary quality (%) |
|---:|---|---:|---:|---:|---:|
| 42 | P0 | 81.3576 | 82.1209 | 79.8308 | 82.1209 |
| 42 | P1 | 81.3979 | 82.0894 | 80.0176 | 82.0866 |
| 42 | P2 | 82.4582 | 83.1255 | 81.1249 | 83.1243 |
| 17 | P0 | 81.1719 | 81.9517 | 79.6122 | 81.9517 |
| 17 | P1 | 81.4496 | 82.1787 | 79.9903 | 82.1800 |
| 17 | P2 | 82.3725 | 83.0430 | 81.0352 | 83.0395 |

| Training seed | P2 passed | Gain vs stronger P0/P1 (pp) | Clean guard | Family guard | Tile clean | Tile family |
|---:|---|---:|---|---|---|---|
| 42 | True | 1.0603 | True | True | True | True |
| 17 | True | 0.9229 | True | True | True | True |

Both seeds pass: **True**.
Main score weights clean, RGB quality and auxiliary quality equally; each family averages its prespecified conditions.
Contrast0.6 and shift8 remain diagnostics outside the gate.

## DSM absence and paired error

| Training seed | Original P2 aux_zero (%) | Same-seed P0 fallback (%) | P0-only correct pixels (clean) | P2-only correct pixels (clean) |
|---:|---:|---:|---:|---:|
| 42 | 81.6224 | 82.1209 | 727251 | 1168212 |
| 17 | 81.5413 | 81.9517 | 681277 | 1236022 |

The same-seed P0 fallback uses an explicit availability mask. Full absence equality with P0 verifies the switch implementation; it does not show learned missing-input detection.
Detailed per-class, per-tile and affected-region integer counts and both confusion matrices are in `decision.json`.
The historical R01 fallback and harm/rescue values remain in each arm summary and are not the same-seed P0 comparison.

## Next decision

Keep the DSM utility candidate. Inspect where P2 introduces errors and DSM absence cost, then design a reliability intervention with matched P0/P1/P2 controls. Plan independent-scene validation after freezing the method and checking prior data exposure.

## Evidence locations and limits

Compact evidence: `records/rebuild_v1_d18_replication_compact_20260928/`.
Full server evaluations: `records/rebuild_v1_d18_replication_20260928/`; training checkpoints: `runs/rebuild_v1/D18_REPL_*_seed17_8000_20260928/`.
Val2 contains only two scenes and was used repeatedly. Seed17 replication does not constitute independent Test6 validation.
The old C0 score is from a different backbone and training start, so absolute performance differences are not attributable to DSM alone.
Check manifest hashes and all six summaries before making another research decision.
