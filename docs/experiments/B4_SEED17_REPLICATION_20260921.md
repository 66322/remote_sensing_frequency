# B4 seed17 replication — frozen protocol

Status: implemented and CPU-tested locally; no server GPU jobs executed here.

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
