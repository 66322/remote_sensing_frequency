# D9B independent-source audit — repository evidence only

2026-09-23 correction: The
[ISPRS Vaihingen page](https://www.isprs.org/resources/datasets/benchmarks/UrbanSemLab/2d-sem-label-vaihingen.aspx)
lists 33 image/DSM patches, and the
[benchmark download page](https://www.isprs.org/resources/datasets/benchmarks/UrbanSemLab/default.aspx)
says complete reference data became available in 2018. The legacy repository
documents exposure of only 12 training and four evaluation IDs. Additional
labelled scenes may therefore exist. The generic D10 directory locator's
zero matches do not exclude Vaihingen: its legacy folders are named
`top/dsm/gts_*`. Run the targeted filename-only inventory
`scripts/inventory_rebuild_v1_vaihingen_unused_metadata.py` before treating
Vaihingen as exhausted. Server availability, actual unused IDs and spatial
independence remain unverified. Historical Potsdam Test6 remains frozen.

User-reported output from the targeted inventory after commit `3afca67`
found 17 filename-level candidates: `2,4,6,8,10,12,14,16,20,22,24,27,29,31,33,35,38`.
The full transcription is in
`records/rebuild_v1_d10_vaihingen_inventory_20260923/user_reported_metadata.json`.
Because the script combined extracted files and ZIP member names from two
roots, this does **not** establish 17 usable triplets. The next check is
`scripts/inspect_rebuild_v1_vaihingen_d10_metadata.py`; it reads metadata
only and reports source paths, header alignment and patch proximity.

User-reported follow-up at commit `f09808b`: all 17 candidates have extracted
optical, DSM and complete-label files, with matching raster dimensions within
each ID. The TIFFs did not expose CRS/bounds to the available `tifffile`
fallback, so `headers_aligned=null` and `nearest_legacy_used=null` mean
**unknown**, not misalignment or isolation. [ISPRS states the TOP and DSM use
the same grid](https://www.isprs.org/resources/datasets/benchmarks/UrbanSemLab/2d-sem-label-vaihingen.aspx).
Its official patch overview also shows all patches cut from one mosaic, with
candidate IDs interleaved with or adjacent to legacy-used IDs. Vaihingen is
therefore available for same-domain development but **not accepted as a
geographically independent D10 final confirmation source**. The compact
transcription is in
`records/rebuild_v1_d10_vaihingen_inventory_20260923/user_reported_header_summary.json`.
The selected `label_complete` path in the inspection output is the eroded
NoBoundary file; an eventual FullGT protocol must choose its separate file
explicitly.

2026-09-23 direction update: The official
[IEEE GRSS 2019 DFC US3D page](https://www.grss-ieee.org/community/technical-committees/2019-ieee-grss-data-fusion-contest/)
describes satellite imagery, LiDAR-derived heights and semantic labels for
training regions in Jacksonville and Omaha. It is a possible *new-domain*
source, not an approved split or a substitute for Potsdam Car analysis.
Verify current access, height-as-input usage, scene IDs, class mapping,
spatial independence and publication terms before any data transfer or run.
The page says its contest validation/test reference labels are undisclosed
and imposes registration and publication-use conditions.

The D9A entropy-route queue has completed. This read-only audit identifies which
labelled scenes are already exposed in the repository; it does not inspect
the server's dataset files or load any image, DSM, label or historical TEST6
tile.

| Dataset | Documented scene IDs | Prior use | D9B status |
|---|---|---|---|
| Potsdam | Train16 in `configs/rebuild_v1/potsdam_split_seed20260915.json` | R01/R05 training | Cannot evaluate these frozen experts independently on their training scenes |
| Potsdam | `3_11`, `5_10` | Repeated Val2 model and method selection | Exploratory diagnostics only |
| Potsdam | `4_10`, `5_11`, `2_11`, `3_10`, `6_11`, `7_12` | Historically exposed TEST6 | Frozen; must not be loaded for D9 selection |
| Vaihingen | `1,3,7,11,13,17,23,26,28,32,34,37` | Earlier F0/P1 training | Not unseen evidence |
| Vaihingen | `5,15,21,30` | Earlier F0/P1 evaluation and comparison | Previously inspected; not an untouched final test |

Vaihingen scene IDs are specified in `scripts/train_vaihingen_formal.py` and
`records/DETPAIR_PREFUSION_FREQ_VAIHINGEN_FROZEN_20260831.md`. The known
Potsdam split covers all 24 documented scenes. No scene set is yet frozen as
independent confirmatory D9B evidence. Complete Vaihingen reference data may
provide additional candidates, pending the targeted inventory and a spatial
neighbor/prior-exposure check.

For D9B, first identify an additional labelled optical+DSM segmentation
scene set or genuinely unused labelled scenes, then freeze scene IDs and
fitting/calibration/evaluation partitions before extracting predictors.
Cross-dataset input bands, resolution, class mapping, DSM normalization and
missingness must be specified. If such a source is unavailable, keep
semantic/frequency benefit modelling as an exploratory protocol and do not
train a deployable safety gate or report an independent generalization claim.
