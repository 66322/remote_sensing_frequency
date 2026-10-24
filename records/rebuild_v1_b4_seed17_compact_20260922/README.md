# B4 seed17 compact evidence — 2026-09-22

## Evidence status

B4 completed all 12 smoke, training, global-robustness and paired-local stages
between 2026-09-21 17:22:07 and 2026-09-22 01:29:52 +08:00. All three formal
runs reached 4000 optimizer steps, the queue finished successfully, and every
retained summary reports that historical TEST6 was not loaded.

The files in this directory were reconstructed from the validated server archiver
output supplied by the user. `server_terminal_output.txt` preserves that source
transcript. The original queue directory, full robust/paired CSV files, preflight
report, logs and checkpoints remain on the server and take precedence if a later
discrepancy is found.

## Global results

Val2 NoBoundary `mIoU_fg5`, percent:

| Model | Clean | DSM down8 | DSM zero |
|---|---:|---:|---:|
| C17 | 86.6027 | 84.9647 | 83.3285 |
| R05_KD17 | 86.1756 | 84.9972 | 83.1646 |
| KD17 | 86.6258 | 85.2065 | 83.2083 |

KD17 minus R05_KD17 is +0.4502 pp clean, +0.2093 pp down8 and +0.0438 pp
DSM-zero. The two global degradation directions therefore repeat the seed42
ordering, although the DSM-zero margin is very small. Against C17, KD17 is
+0.0230 pp clean and +0.2418 pp down8 but -0.1202 pp DSM-zero.

## Paired local damaged-region results

Values are corrupt-minus-clean NoBoundary `mIoU_fg5` changes in percentage
points; a less negative value is better.

| Model | Local missing | Local down8 |
|---|---:|---:|
| C17 | -3.0869 | -1.3499 |
| R05_KD17 | -3.0265 | -1.1459 |
| KD17 | -3.3120 | -1.1831 |

KD17 is worse than R05_KD17 by 0.2855 pp for local missing and 0.0372 pp for
local down8. It is also worse than C17 for local missing by 0.2252 pp. These
directions contradict the seed42 paired-local result.

## Decision

The B4 decision gate **fails**: two global conditions pass, while both local
damaged-region conditions fail. The archiver's four-condition Boolean gate is an
explicit implementation of the decision rule documented before result collection;
it is not a separately preregistered statistical test. The defensible conclusion is
partial global replication with no cross-seed local mechanism replication.

SafeMaxConfidence teacher selection must not be presented as a generally validated
local-reliability or Optical-fallback method. B1–B4 remain useful mechanism and
negative-result evidence. Any new main-method claim requires a revised method,
matched mask-only/calibration controls and evaluation beyond the repeatedly used
two-tile Val2 development split.

`cross_seed_kd_minus_r05_kd.csv` places the seed42 and seed17 KD-minus-R05_KD
effects side by side. Both global degradation columns stay positive, while both
local damaged-region columns change sign.

## Provenance

- Queue: `records/rebuild_v1_b4_seed17_20260921/` on the experiment server.
- Trainer-reported Git HEAD: `abb3d97f3f5d8f4b145c54bfe87bed0a12c6e187`.
- The queue actually used later selectively installed B4 files; source hashes in
  the server preflight package are authoritative where Git HEAD alone is ambiguous.
- Selected checkpoints: C17 step 1500, R05_KD17 step 3000, KD17 step 2000.
- Checkpoint hashes and server paths are recorded in `run_provenance.json`; weights
  are not committed.
- This is random-seed replication on the same Potsdam Train16/Val2 development
  protocol, not independent-dataset or held-out-test validation.
