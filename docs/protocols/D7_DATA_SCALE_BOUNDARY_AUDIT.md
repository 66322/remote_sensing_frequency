# D7 data, sampling, scale and semantic-boundary audit

## Status and purpose

D7 is a diagnostic gate before any class-imbalance training. It asks whether the
existing random crop policy underexposes minority classes, whether small connected
objects fail more often than large ones, whether errors concentrate at true
semantic boundaries, and whether DSM degradation disproportionately harms Car.

D7 does not select or train a new model. Its Val2 results are exploratory because
Val2 contains only two repeatedly inspected development tiles. Historical TEST6
must not be loaded.

## Frozen inputs

- Train16 FullGT labels define class frequencies, crop exposure and component-size
  thresholds.
- Val2 tiles `3_11` and `5_10` provide error diagnostics.
- Existing R01 and R05 checkpoints at seeds 42 and 17 are evaluated.
- Conditions are clean, global DSM down8 and global DSM zero.
- Physical GPU 0 is the only permitted GPU.

## Measurements

The data audit reports per-class pixels, tile occurrence, 8-connected component
areas and 20,000 simulated crops under the current `512 x 512`, scale `0.5–2.0`
policy. Crop pixel counts are area-preserving estimates after nearest-neighbour
resize; they diagnose exposure and are not exact augmented images.

The error audit reports pooled and per-tile FullGT/NoBoundary metrics, per-class
precision/recall/F1/IoU, semantic boundary/interior metrics at radii 1/3/5 pixels,
and component correctness in Train16-defined small/medium/large bins. A component
is recalled when at least 50% of its FullGT pixels receive its class label. This is
an object proxy for semantic masks, not an instance-segmentation metric.

## Predeclared screening flags

These flags choose controlled follow-up experiments; they are not significance
tests or final claims.

1. foreground maximum/minimum pixel ratio is at least 10;
2. Car is absent from at least half of simulated random crops;
3. clean Car component recall differs by at least 5 pp between large and small
   objects for R01 and R05 in both seeds, with at least 20 objects per extreme bin;
4. R05 Car IoU drop under down8 exceeds the five-foreground-class mean drop by at
   least 1 pp in both seeds;
5. clean semantic interior mIoU exceeds radius-3 boundary mIoU by at least 5 pp for
   R01 and R05 in both seeds.

If crop sparsity and the small-object flag both hold, screen mixed class-aware
cropping on R01. If only pixel imbalance holds, screen smoothed weighted CE against
matched CE. If the boundary flag holds, boundary supervision remains a separate
controlled arm. A modality-specific long-tail claim requires the replicated Car
degradation flag and later confirmation on a new frozen evaluation source.

## Outputs

- `records/rebuild_v1_d7_data_sampling_20260922/`
- `records/rebuild_v1_d7_semantic_errors_seed42_20260922/`
- `records/rebuild_v1_d7_semantic_errors_seed17_20260922/`
- `records/rebuild_v1_d7_summary_20260922/decision_evidence.json`
- `records/rebuild_v1_d7_queue_20260922/status.tsv`

Every queue stage has a timeout. Failure is recorded and the queue advances to the
next stage. All persistent paths remain below `/home/jovyan/zzx`.
