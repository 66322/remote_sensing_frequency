# B4 seed17 replication — frozen protocol

Status: complete; the documented decision gate failed.

## Question

Does the seed42 ordering between CE continuation (C), ordinary R05-teacher
distillation (R05_KD), and SafeMaxConfidence-teacher distillation (KD) reproduce
from the independently trained seed17 R01/R05 checkpoints?

## Frozen design

All three arms start from the same selected seed17 R05 16k checkpoint and use the
same seed17 RNG, Train16/Val2 split, augmentation stream, 4000-step scheduler and
training budget. C uses CE only. R05_KD uses the frozen seed17 R05 teacher. KD uses
the frozen seed17 R01/R05 SafeMaxConfidence teacher. No extra fallback KL, SAFE or
average-teacher arm is included. Checkpoint selection remains clean Val2 NoBoundary
fg5 only. Test6 is never loaded.

Primary reporting: clean, DSM-down8 and DSM-zero dataset NoBoundary fg5, plus the
paired local damaged-region corrupt-minus-clean change. Synthetic corruption-interface
bands and per-class results are secondary diagnostics because thin-band class support
caused large quadrant variability in B3. Tiles are validation units; quadrants and
pixels are repeated measurements, not independent replicates. Two seeds establish
replication evidence, not a population-level significance claim.

## Execution limits

Physical GPU0 only and serial jobs. Each arm receives a 20-step smoke before its
fresh 4000-step continuation. A failed smoke skips its dependent training/evaluations;
other arms continue. No retries, automatic resume or overwrites. Hard queue budget
12 hours, individual training limit 4 hours, at least 20 GiB free disk. Expected
wall time is approximately 8–9 hours based on the measured seed42 runs; this is a
planning estimate. Global robustness and paired regional evaluation follow each
successful training run.

## Result closeout

Elapsed time is not completion evidence. After the server queue finishes, run the
read-only archiver from the project root:

```bash
python scripts/archive_rebuild_v1_b4_seed17.py
```

The archiver refuses incomplete queues, missing stages, non-4000-step runs,
invalid TEST6 flags, missing checkpoints and existing output directories. A valid
run creates `records/rebuild_v1_b4_seed17_compact_20260922/` with the global and
paired damaged-region metrics, the predeclared replication gate, checkpoint and
source hashes, queue status and provenance. It reads checkpoints only to hash them;
weights remain on the server and are never copied into the compact package.

The generated decision is still a two-seed result on the same two-tile Val2
development split. Passing B4 supports random-seed replication only; it is not an
independent-dataset or held-out-test conclusion.

## Completed execution

The queue ran from 2026-09-21 17:22:07 to 2026-09-22 01:29:52 +08:00. All
12 arm stages and the final summarizer completed successfully. C17, R05_KD17 and
KD17 each reached 4000 optimizer steps, and TEST6 remained unloaded.

Selected checkpoints were C17 step 1500, R05_KD17 step 3000 and KD17 step 2000.
The trainer recorded Git HEAD `abb3d97`, while the queue used selectively installed
later B4 files. The validated preflight/source hashes and checkpoint hashes retained
on the server therefore define the executed source more precisely than Git HEAD.

## Results

Val2 NoBoundary `mIoU_fg5` (%):

| Model | clean | DSM down8 | DSM zero |
|---|---:|---:|---:|
| C17 | 86.6027 | 84.9647 | 83.3285 |
| R05_KD17 | 86.1756 | 84.9972 | 83.1646 |
| KD17 | 86.6258 | 85.2065 | 83.2083 |

KD17 minus R05_KD17 is +0.4502 pp clean, +0.2093 pp down8 and +0.0438 pp
DSM-zero. Thus the seed42 global degradation ordering repeats, but the zero margin
is nearly neutral. KD17 minus C17 is +0.0230 pp clean, +0.2418 pp down8 and
-0.1202 pp DSM-zero.

Paired damaged-region corrupt-minus-clean changes (pp; less negative is better):

| Model | Local missing | Local down8 |
|---|---:|---:|
| C17 | -3.0869 | -1.3499 |
| R05_KD17 | -3.0265 | -1.1459 |
| KD17 | -3.3120 | -1.1831 |

KD17 is 0.2855 pp worse than R05_KD17 for local missing and 0.0372 pp worse for
local down8. Both local directions reverse the seed42 result.

## Decision

The frozen replication gate fails because both paired local damaged-region criteria
fail. B4 supports only a small, directionally repeated global degradation effect;
it does not reproduce the proposed local reliability-teacher mechanism. Do not
promote SafeMaxConfidence distillation as the validated main method or claim learned
missing-modality detection, local reliability estimation, or inference-time Optical
fallback.

Compact evidence is in `records/rebuild_v1_b4_seed17_compact_20260922/`.
