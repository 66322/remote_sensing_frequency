# D9A entropy-route result provenance

`user_reported_route_comparison.csv` transcribes the rounded server printout
of `scripts/summarize_rebuild_v1_d9a_entropy_route.py` supplied by the user.
The server summarizer reported completion only after checking a zero-failure
17-stage queue, physical GPU0 preflights, Test6 exclusion, deterministic
DSM-zero fallback and R01/R05/safe-confidence agreement with D9A controls.

Original per-condition `method_metrics.csv`, `class_iou.csv`,
`region_metrics.csv`, `selected_harm.csv` and `summary.json` files, plus
`records/rebuild_v1_d9a_entropy_route_summary_20260923/source_manifest.json`,
remain on the server and take precedence. The compact table lacks the
support counts and per-class/size/region results required for a detailed
mechanism conclusion. Blank harm rates under `dsm_zero` mean that the safe
routes selected no R05 pixels, not that the harm rate was measured as zero.

`user_reported_strata_review.json` transcribes the subsequent read-only,
source-hash-verified Car/Building and local-region printout. It preserves the
small selected-pixel denominator behind the seed17 DSM-noise small-Car harm
rate. Original server CSVs remain authoritative.
