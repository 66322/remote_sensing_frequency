# ISFuse transfer assessment — prospective, not queued

Status: source-grounded review and future experiment proposal. No new model
implementation or GPU work; D16/D17 source/config/queue remain unchanged.

## Sources and reading boundary

- CVPR2026 accepted metadata: [CVF](https://openaccess.thecvf.com/content/CVPR2026/html/Wang_Multi-Modal_Image_Fusion_via_Intervention-Stable_Feature_Learning_CVPR_2026_paper.html).
- Method/limitations checked against [arXiv v1 full text](https://arxiv.org/html/2603.23272v1), sections3.2–3.4. CVF main/supplement PDFs returned403 in this session; no claim of checking their full content.
- [Author Train.py](https://github.com/wang-x-1997/Multi-Modal-Image-Fusion-via-Intervention-Stable-Feature-Learning/blob/69a84627542d759179cc5d73356a86b0309191b8/Train.py), main HEAD observed69a84627542d759179cc5d73356a86b0309191b8. Read only, not executed.

Paper-reported mechanism: complementary spatial masking, co-located masking and
whole-modality removal; CFI combines cross-modal attention with local features
through a learned gate; gate-weighted output consistency supports training.
The main task is image fusion, with downstream segmentation evaluation.

Two interpretation issues need resolution before a faithful reproduction:
1. Eq13 and positive beta minimize full-versus-single-modal L1, while the prose
   says maximize. Author CausalNecessityLoss returns positive L1 and training
   adds it with beta0.05. Do not silently reverse the sign and call it original.
2. The code minimizes area deviation minus binary entropy; the entropy part
   favors softer probabilities, not by itself binary decisions. Learned gate
   values are not directly calibrated measurements of stability or causal utility.

These are equation/code interpretation findings, not evidence that all reported
experimental results are invalid. Other papers in the user list are not audited
by this focused review.

## Evidence chain in our project

- D15: experimentally verified exploratory DSM-only capability and useful
  existing R05 complementarity under some RGB degradations. No universal
  reliability or causal identification claim follows.
- D14: model response to DSM intervention is experimentally observed;
  sensitivity alone does not establish benefit or a shortcut mechanism.
- D13: reducing harm also suppressed rescue substantially. This is direct
  motivation to check whether a new consistency mechanism simply ignores DSM.
- D16 A1/A2: code implements prediction KL, including training-label-based
  correctness selection for A2. There is no CFI module, learned stability gate,
  explicit feature invariance loss, complementary two-stream masking or
  co-located two-stream masking. Do not rename this running experiment as an
  ISFuse reproduction. Its result is still pending.
- D17 B1/B2: geometric auxiliary supervision is a different hypothesis.

## Transfer hypothesis, not a demonstrated contribution

Controlled observation loss could improve RGB–DSM feature integration when
paired with segmentation supervision, retaining useful complementary evidence
while resisting nuisance changes. This is a testable engineering hypothesis,
not a claim that masking identifies real-world causal structure.

Distinguish three interventions: suppress nuisance without changing scene
semantics; remove potentially useful evidence; misalign evidence. Useful
features need not remain numerically unchanged after the evidence is removed.
Simultaneous masking can reward context memorization and cannot prove
cross-modal compensation. Constant predictions or complete DSM neglect can
also look stable. Track clean accuracy, rescue and harm jointly.

Use segmentation CE as the primary task objective. RGB intensity and DSM
height are different physical quantities; do not copy intensity-fusion fidelity
targets or force equality of raw cross-modal features. Both-input absence
regions must be reported separately and excluded from strong local consistency
when neither modality supports the semantic target. Missing-modality inference
should remain useful, not deliberately deteriorate to make a branch necessary.

## Reserved first screening matrix

Freeze one modest CFI-inspired insertion, one structured-mask distribution,
one training budget and one evaluation protocol before running. Every row
uses the same views/initial anchor/crops/optimization budget; added module
initialization must not alter data RNG. This is a segmentation adaptation,
not a reproduction of original image fusion results.

|Arm|Fusion|Additional objective beyond paired segmentation CE|
|---|---|---|
|C0|Current fusion|None; structured masking only|
|C1|Current fusion|Ordinary output consistency|
|C2|CFI-inspired|None|
|C3|CFI-inspired|Ordinary output consistency|
|C4|CFI-inspired|Task-conditioned consistency preserving useful corrections|
|C5|Same as C4|Class/count-matched shuffled task weights|

C0–C3 separate module benefit from training-consistency benefit. C4 versus C3
tests task conditioning; C4 versus C5 tests meaningful spatial placement.
Assess whether C2's additional parameters alone explain improvement. Existing
D16 A0 can be a historical matched-budget reference if its exact inputs,
starting weights and optimization match; it cannot replace C0's changed-mask
control. New held-out intervention evaluations can reuse existing checkpoints.

Start with seed42 for six pilots after the current batch. This screens
feasibility only. Replicate promising arms AND necessary matched controls at
seed17, rather than automatically doubling every failed exploratory variant.
No launch date, coefficients, step count or resources are frozen by this note;
final executable protocol must use D16 outcomes and measured throughput.
Do not append silently to the currently running finite queue.

Evaluation must include clean images, RGB and DSM damage, known absence,
held-out perturbation type/severity, per-tile/per-class results and harm/rescue.
Report paired full-versus-removed changes as model sensitivity/utility proxies,
not automatically causal effects. A stable-but-useless solution fails. A
method matching simple consistency or shuffled weighting has not established
its proposed mechanism. More Val2 sweeps do not create independent evidence;
Test6 remains prohibited and independent scenes are needed for confirmation.

## Thesis wording

Suggested hypothesis wording: We investigate controlled modality interventions
and task-constrained consistency to improve RGB–DSM complementary feature
learning, and evaluate whether the method preserves useful corrections under
input degradation. Avoid claims of eliminating shortcuts, identifying true
causal relations, guaranteed reliability, or novelty based only on transferring
an existing operator to another dataset. Attribute borrowed masking/CFI ideas.
