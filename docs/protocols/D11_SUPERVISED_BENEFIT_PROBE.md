# D11: supervised fixed-expert decision-benefit probe

Status: implemented; server execution pending. This is new supervised model
work, not another D10M fixed-score/radius search. No residual segmentation
gate or backbone is trained. D9B and D10M remain negative results.

## Question and scope

Can a small learned predictor distinguish rescue from harm using available
expert outputs, with a threshold frozen off Val2? Does adding the existing
multiscale energy/correspondence input improve that predictor?

The target is three outcomes on expert disagreements: R05-only correct
(gain), R01-only correct (harm), and both wrong (neutral). This is a discrete
decision-benefit target, not regression of continuous CE delta. Continuous
CE delta is still used as a secondary ranking diagnostic. The predicted
score is P(gain)-P(harm); no attention/energy quantity is called reliability.

## Frozen roles and exposure

The exact protocol is `configs/rebuild_v1/d11_supervised_benefit_probe.json`.
Tile roles were selected without using their new probe outcomes:

| Role | Tiles |
|---|---|
| Head fit | 6_7, 6_8, 6_9, 7_7, 7_8, 7_9 |
| Probability temperature | 6_10, 7_10 |
| Routing threshold | 4_11, 7_11 |
| Exploratory evaluation | Val2: 3_11, 5_10 |

All ten development tiles belong to Train16 and were seen by both experts.
Thus fit/calibration errors are in-sample with respect to the experts, even
though head roles are tile-disjoint. Val2 was repeatedly inspected and used
for expert selection. This is a feasibility probe, not independent final
generalization, cross-fitting, a clean test set or statistical safety guarantee.
Different IDs do not prove geographic separation. No dataset audit is needed
to state this limitation. Historical Test6 remains prohibited.

Seeds 42/17 use their own matched, frozen 16k R01/R05 pair throughout.
Here 16k is the completed training budget: the selected best checkpoint can
be earlier. Match checkpoint paths and actual selected steps between new
development manifests and old D10M manifests, rather than requiring both
best checkpoints to have global_step=16000.
Fit and both calibration stages see clean, blur5 and noise std0.10 only.
Evaluation uses those conditions plus circular shifts 4/16/32 and DSM zero.
Shift is held out from **head** development, not necessarily expert training.
Edge-filled duplicates are excluded from this evaluation matrix. Local
missingness, downsampling, stronger noise and RGB failure remain future work.

## Models, sampling and calibration

Uniform NoBoundary 50k-pixel samples per development tile/condition; the same
coordinates across conditions/seeds, no class or outcome resampling. Keep all
samples for threshold denominators; fit three-way softmax on disagreements.
Require at least 20 of each target across fit data or fail explicitly.

Six prespecified L2 multinomial logistic probes, one per seed:

1. confidence margin alone;
2. entropy margin alone;
3. JS disagreement alone;
4. expert outputs: both six-class probability vectors, confidence/entropy
   margins, JS and both entropies (17 features);
5. local frequency/structure features at radii 2/8/32 (9 features);
6. expert outputs plus those features (26 features).

The first three are supervised calibrated scalar baselines. They are not
raw class confidence interpreted as benefit probability. Raw safe-confidence
and safe-entropy decisions remain additional controls.

Frequency energies use a fixed log1p(10000*x) transform; all inputs are
standardized using fit data only. Same L2=0.01, L-BFGS-B, max 300 iterations;
no hyperparameter search. Failed convergence is a failed model job.
No class weighting is applied: retain natural disagreement outcome rates.
All models use the same linear architecture/regularization, but feature
counts differ (6/54/30/81 classifier coefficients for scalar/expert/frequency/full,
excluding the common temperature and fitted preprocessing statistics).
An observed feature increment is therefore not a parameter-matched causal
attribution; capacity controls are required before that claim. Predicted
class probabilities are expert-output context, not deep semantic prototypes.
Learned semantic representations and faithful SGMA/CAF-Net comparisons are
not implemented by this experiment.

Fit one scalar temperature in [0.25,4] on the two probability-calibration
tiles. Then select one threshold per seed/model, shared across conditions,
on the separate two threshold-calibration tiles. Fixed grid 0..1 step0.05,
strict score>threshold; 1 permits all-RGB fallback. Choose highest mean
rescue satisfying empirical H<=0.005 in **every** calibration tile-condition
group; ties prefer higher thresholds. H denominator includes all sampled
valid pixels, not just disagreements. No statistical guarantee is implied.

Serialize/fingerprint the fitted model, temperature and chosen threshold
before opening any Val2 sample file. Never update them during evaluation.
Known missing DSM forces RGB deterministically. Expert agreement also selects
RGB because switching experts cannot change the predicted label there.

## Evaluation and decision

Reuse existing D10M NPZ samples: no new Val2 GPU inference. Verify manifest
seed/condition/tiles/checkpoint step and record source hashes. Evaluate the
same samples for probe, RGB, raw dual, safe confidence, safe entropy and
availability-aware correctness oracle. Report pooled sample confusion-matrix
mIoU, H/R and coverage; by tile, seed, class, small Car and interior/all.
These are **sampled NoBoundary mIoU**, not complete-image results. The size
of small-Car strata and sampling noise can preclude fine difference claims.

Report AUROC/AP for gain vs harm on flip cases, secondary CE-benefit ranks,
and ECE/Brier for calibrated gain/harm probabilities conditional on available
expert disagreements (both-wrong cases included for calibration). Do not
report these calibrated events as CE-benefit probabilities. DSM-zero
calibration/ranking is NA, since availability disables routing.

Primary screening at group=all: evaluate each prespecified model against
the stronger calibrated confidence/entropy probe per condition. Average four
families equally (clean, blur, noise, mean of three shifts), avoiding triple
weighting of shifts. A candidate merits full-resolution confirmation only if,
for **both** seeds:

- family-average sampled mIoU increment >=0.10 pp over that scalar comparator;
- clean sampled mIoU >= RGB;
- H<=0.5% on every evaluated tile-condition group.

These are practical screening rules, not significance tests or guarantees.
No method/threshold is selected to optimize Val2 after the fact. Passing
only nominates that predeclared model for a frozen full-resolution comparison;
it does not authorize residual-gate training. Full feature vs expert-only
increment is printed separately. If nothing passes, close this linear probe
without increasing capacity or tuning thresholds on the same Val2 results.

## Execution

`scripts/run_rebuild_v1_d11_probe_queue.sh` executes numerical tests, one
export smoke, 20 seed-tile exports (3 conditions each), 12 CPU probe fits and
the final summary. RGB inference is reused across conditions within each
export job. No automatic download. GPU 0 only; runtime outputs, model JSON
and caches under /home/jovyan/zzx; failures continue; timeouts bound each job.
Existing queue/output records are never silently overwritten.

Read D11_SUMMARY.log and the status tail after completion. The summary lists
missing models and returns nonzero for incomplete runs rather than declaring
them a successful experiment. No follow-up source inventory is requested.
