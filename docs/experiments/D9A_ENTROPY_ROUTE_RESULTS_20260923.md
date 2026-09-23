# D9A safe-entropy routing decision audit

The user-reported server summarizer completed after validating the 17-stage
queue with zero failures, physical GPU0 preflights, Test6 exclusion and exact
R01 fallback for both safe routes under complete DSM absence. It compared
R01/R05/safe-confidence mIoU against the earlier D9A outputs, using the
corrected local-down8 `fix1` results, and found agreement within 1e-4
absolute mIoU. The source-hashed original CSVs and manifest remain on the
server; the committed rounded transcription is under
`records/rebuild_v1_d9a_entropy_route_compact_20260923/`.

**Decision:** direct entropy difference was the better *CE-benefit ranking*
score in all 16 D9A rows, but simply routing to the lower-entropy expert
does not improve the matched safe-confidence route. Safe entropy wins NB
mIoU in 4/16 seed-by-condition rows, loses in 10/16 and ties in both DSM-zero
rows. Its mean paired difference is **-0.0089 pp**. On clean DSM it loses
0.0179/0.0141 pp for seeds 42/17. These differences are descriptive Val2
results, not independent-scene significance estimates.

Under normalized Gaussian DSM noise sigma 0.10, safe entropy improves on
safe confidence by 0.0343 pp at seed42 but loses by 0.0966 pp at seed17.
Both routes remain below R01: safe entropy by 0.1471/0.4156 pp at seeds
42/17. The selected-dual CE-harm rate for safe entropy is 17.03%/20.13% in
that condition. Under complete DSM absence both safe routes exactly equal
R01 and select no R05 pixels. The selected-harm denominator is selected R05
pixels, so it must be read alongside selection counts and mIoU; lower harm
rate by itself does not imply better segmentation.

The seed/condition differences rule out a claim that lower predictive entropy
is a reliable plug-in replacement for D5 safe confidence. Entropy remains a
strong *ranking baseline* that any learned benefit predictor must beat. This
stage does not test semantic prototypes, frequency quality, fitted feature
combinations or calibrated benefit probabilities, and it does not satisfy the
full D9 gate. No safety residual gate should be trained from this result.

Per-class IoU, small-Car selected harm and local damaged-region metrics are
available in the original server outputs. Run the read-only, source-hash
checking `scripts/print_rebuild_v1_d9a_entropy_route_strata.py` before a
class-specific mechanism conclusion. The known Potsdam and
historical Vaihingen scenes are already exposed; see
`docs/current/D9B_SOURCE_STATUS_20260923.md` for the independent-source
boundary before D9B fitting.
