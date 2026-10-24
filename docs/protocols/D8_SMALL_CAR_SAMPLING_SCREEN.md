# D8 small-Car sampling causal screen

D8 tests whether the replicated small-Car error can be changed by crop selection
without changing loss, architecture, data split or initialization. C uses random
crops, A replaces 20% with any-Car-centred crops, and S replaces 20% with
small-Car-centred crops. Small Car is frozen as Train16 component area <= 2117
pixels. Tiles remain uniformly sampled.

All arms start from the same R01 seed42 checkpoint, use fresh matched AdamW
optimizers and run exactly 4000 steps. Step 4000 is the decision checkpoint;
intermediate Val2 measurements cannot select a checkpoint. Historical TEST6 is
prohibited. This is a development screen, not a final paper result.

S passes only if versus C it improves small-Car recall@50 by >=3 pp, small-Car
mean correct fraction by >=2 pp and Car IoU by >=0.5 pp, while Car precision loses
no more than 1 pp and NoBoundary mIoU loses no more than 0.3 pp. Per-tile small-Car
mean correctness must move in the same direction. A separates generic Car exposure
from size-specific sampling. Only a passing winner may be replicated at seed17.
