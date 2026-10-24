# B2/B3 compact evidence snapshot — 2026-09-21

## Evidence status

This directory is a compact transcription of completed server outputs supplied in the working conversation. It is intended for cross-computer handoff and conclusion auditing. It is not a replacement for the original server CSV files, checkpoints, logs or confusion matrices.

- Dataset/split: Potsdam Train16 -> Val2 (`3_11`, `5_10`)
- Primary metric: `mIoU_fg5(noboundary)`
- Seed: 42
- Test6: not loaded
- B2 queue: `records/rebuild_v1_b2_night20260920_v1/`
- B2 observed interval: 2026-09-20 23:34:59 to 2026-09-21 05:34:42 +08:00
- R05_KD training interval: 2026-09-20 23:59:55 to 2026-09-21 02:38:08; selected step 1000; reported peak 14.5058 GiB
- AVG_KD training interval: 2026-09-21 02:50:16 to 05:28:22; selected step 1000; reported peak 14.4964 GiB
- B3 paired evaluation: `records/rebuild_v1_b3_paired_20260921/`
- Source type: user-supplied terminal output; original artifacts remain on the server

Files:

- `global_metrics.csv`: clean, global DSM down8 and global DSM zero results for five matched seed42 arms.
- `paired_family_metrics.csv`: paired corrupt-minus-clean changes inside the damaged region and its interface boundary.
- `paired_tile_metrics.csv`: the supplied per-tile mean, worst and best paired changes for all five arms.
- `SHA256SUMS`: integrity hashes for the three compact CSV files.
- `docs/experiments/B2_B3_RESULTS_20260921.md`: interpretation and thesis claim boundary.

## Reproducible headline comparisons

Compared with the matched CE continuation C, ordinary safe-teacher KD changes the primary metric by +0.2247 pp on clean, +0.5275 pp on global DSM down8, and +0.6918 pp on global DSM zero. SAFE adds +0.0775 pp over KD on clean and +0.1627 pp on down8, but is -0.1679 pp on DSM zero. The explicit fallback penalty therefore has no consistent advantage over KD.

The R05-only teacher control (`R05_KD`) is +0.2217 pp above KD on clean, but -0.2220 pp on down8 and -0.1568 pp on DSM zero. In the paired local diagnostic, KD has a smaller degradation than R05_KD in all eight tile x corruption-family x region comparisons. This supports a reliability-aware teacher-target effect within seed42, but does not establish a universal robustness gain over CE.

## Archival rule

After the seed17 B4 queue completes, copy or transcribe its compact summary into GitHub before changing computers. Do not commit checkpoints or large prediction arrays; commit aggregate CSV/JSON, configuration identity, completion markers, hashes where available, and server paths.
