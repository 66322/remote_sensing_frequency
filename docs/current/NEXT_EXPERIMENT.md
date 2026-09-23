# Next experiment - D11 supervised benefit probe

D9A/D9B/D10M results are extracted and their fixed-score branches remain
closed. D11 is now implemented; no server run or result is claimed yet.
No new data download or source inventory is required.

Run `scripts/run_rebuild_v1_d11_probe_queue.sh` in remote_sensing from the
server project. It automatically exports development samples, fits the
supervised heads, calibrates them, evaluates existing Val2 caches and prints
D11_SUMMARY.log. The frozen protocol is
`docs/protocols/D11_SUPERVISED_BENEFIT_PROBE.md`.

## Concrete experiment

- Frozen expert pairs, seeds42/17. Six fit tiles, two temperature-calibration
  tiles and two threshold-calibration tiles, all from Train16. No role overlap.
- Export 50k matched samples per development tile under clean, blur and noise;
  infer RGB once per seed/tile and reuse across the three conditions.
- Fit six tiny three-class linear models: confidence, entropy, JS, expert
  outputs, frequency/structure, expert+frequency. No backbone or residual gate.
- Learn gain/harm/both-wrong outcomes on expert disagreements. Calibrate gain
  and harm probabilities on separate tiles; select one condition-agnostic
  threshold subject to empirical H<=0.5% in every threshold-calibration group.
- Freeze model and threshold before opening Val2. Reuse D10M caches, including
  head-held-out shifts. Missing DSM deterministically selects RGB.
- Print sampled NoBoundary mIoU, actual harm/rescue, gain/harm ECE and Brier,
  benefit ranking and class/size strata. Do not confuse sampled results with
  previous complete-image mIoU.

## Interpretation and one-batch stop

The experts saw all Train16 development tiles, and Val2 was repeatedly used
for earlier decisions. This experiment is exploratory, not independent
confirmation or formal risk control. Predicted class probabilities do not
constitute a deep semantic prototype method. Frequency adds model parameters;
its increment alone does not establish mechanism or novelty.

The summary predeclares a candidate screen for each model: both seeds must
have >=0.10 pp family-average sampled mIoU gain over the stronger calibrated
confidence/entropy control, no clean regression versus RGB, and H<=0.5% for
every evaluated tile-condition. These are practical screening rules, not
significance tests. A pass leads only to a frozen full-resolution comparison.
No pass: close this linear probe, without changing thresholds/capacity on
Val2. No automatic residual-gate training in either case.

Runtime writes stay under /home/jovyan/zzx, physical GPU0 only, timeout-bound
serial jobs continue after failure. Test6 remains frozen. The queue refuses
to overwrite existing records. No new dataset audit follows this batch.
