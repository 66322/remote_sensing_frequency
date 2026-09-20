# Conditional follow-up plan — 2026-09-20

Status: proposals only. B1 is running; no results or automatic new launches.
Maintain GPU 0, zzx boundary, failure-continue policy and historical TEST6 exclusion.

## P0 — Close and archive the running B1 pilot

Read C, KD and SAFE full results, not just the summary Boolean. Preserve the
original 4k schedule, clean-checkpoint rule and exploratory thresholds. Save
all outcomes, including failures. Compare each arm to C and the two-expert
teacher; report the clean/zero/down8 trade-off rather than only its average.

If KD matches or beats SAFE, prefer the simpler KD unless local evidence
supports the extra weighting. If both fail to improve over C, do not
automatically extend to 16k; inspect learning curves and condition failures.
A passing SAFE flag does not authorize selecting it over better KD.

## P1 — Low-cost fairness checks, no new training

- Compare safe_max_confidence, safe_prob_avg, safe_prob_alpha25 and
  safe_min_entropy with identical missing-region fallback, on both existing seeds.
- Add deterministic condition-rule fallback as a deployment baseline.
- Evaluate all completed B1 arms on local missing/degraded masks; report whole
  image, damaged, intact and boundary-adjacent regions plus class-level results.
- Report family mean, worst condition, and per-condition gains over R01/R05.
  Define aggregation before inspecting results.
- Separate known valid-mask use from inferred-zero use. Check natural zero
  false positives and metadata masks; general missing detection is a separate task.
- Benchmark R01, R05, the two-expert system and student using the same input,
  hardware, warmup, repeats, preprocessing and timing scope. Report train cost too.

These checks reuse existing checkpoints. Running scripts must first be
implemented and reviewed; this document is not a claim that they already exist.

## P2 — Mechanism controls only if distillation shows benefit

Freeze identical initialization, treatments, continuation budget and seeds:
(a) ordinary R05-teacher KL, and
(b) matched safe-average-teacher KL.
These distinguish distillation benefits from the particular teacher routing
rule. Existing C/KD/SAFE isolates continuation and missing-region reweighting.

If simpler controls match the candidate, simplify the method and reduce
novelty claims. Do not add frequency/alignment/gating blocks to rescue a name.

## P3 — Independent evidence after selecting a method

- Fix the method, hyperparameters and checkpoint selection before replication.
- Run seed17 then a third prespecified seed for the candidate and essential
  controls, not every historical ablation.
- Choose a second Optical/DSM dataset with a documented train/validation/test
  policy. Audit historical Vaihingen exposure before treating any split as new.
- Prespecify unseen mask shapes/severities and distinct DSM corruption types.
  Prefer documented real NoData/quality issues where available.
- Include FullGT and NoBoundary, per-class IoU, damaged/intact metrics and
  efficiency; report sample units and uncertainty honestly.
- Historical Potsdam TEST6 remains exposed and cannot become an honest sealed test.
- Any longer training schedule must state whether it is fresh training or
  continuation, specify total history/cost, and retain a matched control.
  There is no automatic “pilot passed, therefore add 16k” rule.

## Related-work priorities and claim boundary

Closest verified examples include OGP-Net (AAAI 2025), sensor-failure benchmarking
(CVPR Workshops 2025), DIS2 (WACV Workshops 2026), STARS (January 2026 preprint),
and Multi-to-Uni Modality Knowledge Distillation for Remote Sensing Image
Semantic Segmentation (online August 2026).
Implementations and protocols must be checked before numeric comparison.
Select a feasible directly comparable robust-segmentation baseline, not only
ordinary clean-fusion networks. Paper-table scores on other splits are not
comparable to this Val2 score.

- https://ojs.aaai.org/index.php/AAAI/article/view/32743
- https://openaccess.thecvf.com/content/WACV2026W/CV4EO/papers/Kieu_DIS2_Disentanglement_Meets_Distillation_with_Classwise_Attention_for_Robust_Remote_WACVW_2026_paper.pdf
- https://arxiv.org/abs/2601.17342
- https://doi.org/10.1016/j.inffus.2026.104696

A possible research claim is reducing negative transfer from spatially failing
DSM while retaining its useful contribution with single-model inference.
It is a hypothesis, not an established innovation. Current evidence supports
development diagnostics, not an acceptance probability or guaranteed journal tier.
