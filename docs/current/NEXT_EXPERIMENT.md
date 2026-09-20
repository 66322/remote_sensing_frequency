# Next Experiment: D5 Confidence Routing

- Status: code ready; server execution pending
- Models: frozen R01 and R05, seeds 42 and 17
- Training: none
- Device: physical GPU 0 only
- Dataset: Potsdam Val2 only; historical TEST6 prohibited

D4 rejects a degradation-only reliability gate because R05 beats R01 in local
down8 regions at seed42 but loses at seed17. D4 nevertheless finds 3.53-4.30 pp
mean pixel-oracle headroom, so expert errors are strongly complementary.

D5 tests whether this complementarity is recoverable without training:

- equal and fixed-weight probability fusion;
- maximum-confidence routing;
- minimum-entropy routing;
- maximum-confidence routing with forced Optical fallback in known missing
  regions.

Conditions are clean, global DSM zero/down8, four local-zero quadrants and four
local-down8 quadrants. Both seeds must pass the same rule: clean and down8
within 0.2 pp of the best expert, and DSM-zero within 0.2 pp of R01.

Run `scripts/run_rebuild_v1_d5_queue_20260920.sh`. If no nonlearned method
passes both seeds, the next model is a benefit-aware router supervised by expert
correctness/disagreement, with a hard Optical fallback mask.
