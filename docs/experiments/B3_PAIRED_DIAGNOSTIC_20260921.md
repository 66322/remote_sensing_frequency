# B3 paired local-failure diagnostic — 2026-09-21

Status: implemented and CPU-tested locally; no server GPU evaluation executed here.

## Question and design

The B2 tables report absolute regional scores after local DSM damage. They do not
establish how much performance changed because clean predictions were not scored on
the exact same corruption-defined pixels. B3 evaluates the selected C, KD, SAFE,
B2-R05 and B2-AVG checkpoints without training or checkpoint selection.

For every model, Val2 tile, local corruption and region, B3 compares clean and
corrupted predictions on exactly the same pixels. It reports corrupt-minus-clean
FullGT and NoBoundary metrics, per-class counts, and clean-correct/corrupt-wrong versus
clean-wrong/corrupt-correct transitions. The tile is the independent validation unit.
Pixels and the four quadrant placements are repeated measurements, not independent
replicates. Family summaries are descriptive only.

The synthetic interface band is +/-8 pixels in Chebyshev distance and overlaps the
damaged and intact masks. It is the artificial corruption interface, not a semantic
object boundary. No test6 data are loaded. No GT value controls inference or routing.

## Gate

Use this result to decide whether the previously observed low interface scores reflect
damage-induced decline, regional difficulty already present in clean predictions, or
both. Do not start a new routing/gating model from absolute interface scores alone.
After this diagnostic, the next confirmatory job is a matched seed17 replication of
C, KD and ordinary-R05-teacher KD; it requires separate seed17 configs and checkpoint
binding checks and is not included in B3.
