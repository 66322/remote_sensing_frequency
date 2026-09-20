# Next Experiment: D4 Expert Complementarity

- Status: code ready; server execution pending
- Priority: only active experiment
- Models: paired R01 Optical-only and R05 Optical+DSM
- Seeds: 42 and 17
- Training: none; existing best checkpoints only
- Device: physical GPU 0 only
- Dataset: Potsdam Val2 only
- TEST6: prohibited

## Why D4 is required

D1-D3 show that R05 is strongly preferable to the capacity-matched control
inside locally down8 DSM regions, but it does not retain an Optical-safe path
when DSM is missing. A1 and A2 show that changing dropout probability alone
cannot remove this tradeoff without reducing clean performance.

Before training a learned reliability gate, D4 must establish that R01 and R05
make complementary errors at the same pixels and regions.

## Protocol

For seed42 and seed17, evaluate paired R01 and R05 predictions under:

- clean;
- global DSM zero and down8;
- four local-zero quadrants;
- four local-down8 quadrants;
- 2, 4 and 8 pixel shifts in four directions.

Report four methods:

1. R01 Optical-only;
2. R05 Optical+DSM;
3. a condition-aware rule using R01 only in known missing regions;
4. a label-informed pixel oracle as an upper bound.

Also report both-correct, only-R01-correct, only-R05-correct and both-wrong
pixel fractions, plus damaged/undamaged regional metrics.

## Go/no-go rule for B1

Proceed to the frozen-expert local gate only if both seeds show:

- R01 is better inside local DSM-missing regions;
- R05 is better inside local down8 regions;
- mean pixel-oracle headroom over the better expert is at least 0.5 pp.

If this gate passes, B1 uses:

`Zsafe = Zopt + g(x, dsm) * (Zdual - Zopt)`

Both experts remain frozen during the first pilot. Only the spatial reliability
map `g` is trained.

## Execution

Use `scripts/run_rebuild_v1_d4_queue_20260920.sh`. The queue performs a seed42
smoke test, both formal seed evaluations and the cross-seed decision summary.
It enforces physical GPU 0, project-path boundaries and per-stage timeouts.

Expected output directories:

- `records/rebuild_v1_d4_expert_complementarity_seed42_20260920/`;
- `records/rebuild_v1_d4_expert_complementarity_seed17_20260920/`;
- `records/rebuild_v1_d4_expert_complementarity_summary_20260920/`.
