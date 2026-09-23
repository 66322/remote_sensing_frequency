# D10M: spatial correspondence versus frequency amplitude

Status: reported complete, primary structure-score criterion failed. See
`docs/experiments/D10M_RESULTS_20260923.md`. This protocol is closed; the
execution instructions below are retained for provenance, not a rerun request.

## Why now

External-data acquisition became an unnecessary prerequisite for exploratory
mechanism work. Stop that detour. D9B closed its fixed handcrafted combinations,
not all semantic/frequency representations. D10M implements the previously
proposed amplitude-preserving spatial perturbation and harm/rescue experiment.
It does not repeat the failed weighted sums or fit a safety gate on Val2.

## Frozen experiment

- Existing R01/R05 16k checkpoints, seeds 42 and 17; Potsdam Val2 only.
- Ten conditions: clean; circular horizontal shifts 4/16/32 px; edge-filled
  horizontal shifts 4/16/32 px; existing blur5; noise std0.10; DSM zero.
- Circular shifts preserve full-tile Fourier amplitude. Check relative L2
  error <=1e-6; do not assert that local frequency energy stays unchanged.
- Circular wrapping is artificial. Edge-filled shifts are the non-wrapping
  control. Primary evaluation excludes patch+32 pixels from every tile edge
  for every condition (544 px with the frozen 512 px patch). Full-tile
  NoBoundary metrics are secondary. This avoids directly evaluating wrapped
  borders; it does not prove all boundary or model-context confounding absent.
- Physical GPU 0, serial queue, individual failure continues; finite timeout.
  No overwriting previous run directories. All server outputs under /home/jovyan/zzx.
- No Test6, no new expert training, no external dataset and no learned fusion.

## Measurements

1. Full-tile Fourier-amplitude error and sampled CE(R01)-CE(R05). This is
   relative benefit of the fixed expert pair, not a pure causal DSM effect.
2. Exact NoBoundary confusion matrices converted to mIoU, Car/Building IoU,
   with pooled results computed from summed matrices rather than mean tile IoU.
3. For R01, R05, safe confidence, safe entropy and correctness oracle:
   H=P(R01 correct, method wrong), R=P(R01 wrong, method correct), denominator
   all valid pixels within the stated region. R-H is accuracy change, not mIoU.
4. Paired sample (200k/tile) feature cache: coordinates, labels, object size,
   interior mask, both expert probabilities, continuous CE delta, confidence,
   entropy, JS, optical/DSM local band-pass energy, and absolute local
   cross-modal residual correlation at radii 2/8/32. Labels are evaluation
   targets only. Features never read labels. These descriptors are neither
   learned semantic prototypes nor SGMA/CAF-Net reproductions.
5. Decision-benefit AUROC/AP among correctness-flip pixels; report support
   and prevalence. Report by tile, seed, class and small Car. Unsigned JS
   and energy are descriptive weak controls, not signed benefit probabilities.
6. Tie-aware harm-rescue envelope at H<=0,0.1%,0.5%,1%,2%. Whole score ties
   are retained. Thresholds are chosen post-hoc to describe ranking capacity;
   these are NOT calibrated deployable policies. Primary descriptor is r8
   structure at H<=0.5%, compared with the stronger confidence/entropy
   control per tile/condition. Other scales are descriptive, not selected winners.
7. Known DSM-zero availability disables dual selection in safe policies and
   curves. R05 remains an unsafe raw-expert diagnostic control. No ECE for
   raw scores; calibrated benefit probabilities do not yet exist.

## One-run decision, no audit loop

If circular amplitude is preserved but dual benefit/mIoU declines with shift,
the result demonstrates that global amplitude alone does not characterize
this expert pair's utility. It does not prove the proposed new cues useful.
Compare circular and edge-filled interior results before interpreting this.

If structure cues fail to retain rescue against confidence/entropy under
matched harm for both seeds, do not optimize thresholds/weights on Val2 or
claim semantic-frequency gating validated. Retain a negative mechanism result.
If evidence is promising, preregister a bounded **learned benefit predictor**
ablation with confidence/disagreement, semantic-only, frequency-only,
semantic+disagreement and full features, fit/calibrate on separate scene groups.
Use a feasible local exploratory split first; independently held-out scenes
remain necessary for a final generalization claim. D10M alone never clears
the residual-gate training criterion.

After this batch, report the mechanism conclusion and choose that next fit
or close the feature hypothesis. Do not request another directory inventory.
Learned semantic features, probability calibration, held-out corruption
families, full/local RGB failure and independent confirmation remain unfinished.
Existing D9 results are preserved; B1-B4 remain closed.

## Execution

Run `bash scripts/run_rebuild_v1_d10m_mechanism_queue.sh` from the server
project with the remote_sensing environment. It runs one smoke, 20 paired
seed-condition jobs, and the summary automatically. Read queue status and
`D10M_SUMMARY.log` after completion. No separate audit stage is required.
