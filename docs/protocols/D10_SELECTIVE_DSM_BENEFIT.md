# D10 design freeze: selective DSM benefit, pending independent source

Status: **method design only; no dataset accepted, no training queue launched**.
This is a materially new hypothesis after the failed D9B fixed-score screen,
not a reweighting of its six Val2 scores. Historical Test6 stays frozen.

## Research claim to test

When RGB and RGB–DSM experts disagree, predict whether adding DSM changes
the decision beneficially. Route to the dual expert only when its estimated
decision benefit exceeds a calibration threshold. Known DSM absence overrides
the predictor and returns the RGB expert exactly. The contribution would be
the target and risk-controlled selection, not a claim that semantic prototype
similarity, frequency energy or attention is itself true reliability.

For true label `y` and frozen expert predictions `a=argmax ZRGB`,
`b=argmax Zdual`, define on pixels with `a != b`:

- `t=+1` when `b=y` and `a!=y` (dual-only-correct);
- `t=-1` when `a=y` and `b!=y` (RGB-only-correct);
- `t=0` when both are wrong.

Agreement pixels are counted but excluded from the primary decision head,
because switching experts cannot change their argmax label. The continuous
cross-entropy difference remains a secondary diagnostic; D9A showed that
ranking it better need not improve routed mIoU. No ground-truth class or
component size enters the predictor.

## Minimal model and required controls

Start with a shallow three-output head trained on frozen expert features,
probabilities and logits. It estimates the three outcome probabilities
`p+`, `p-`, `p0`; its decision score is `p+ - p-`. Spatial context, learned
semantic features and observable RGB/DSM frequency-quality descriptors may
be added only as named ablations with the same training scenes and capacity
budget. This guards against crediting a generic larger fusion model.

At inference use `choose_dual = availability_DSM & disagreement &
(p+ - p- > tau)`, where `tau` is fixed on a separate calibration partition.
The first stage is a **hard expert selector**. Do not train the soft residual
`ZRGB + availability * gate * (Zdual - ZRGB)` until hard selection passes
the decision and segmentation gates. A zero-availability unit test must
verify bitwise/equivalent RGB output for complete and local missingness.

Minimum matched controls: R01, R05, D5 safe confidence, safe entropy,
an oracle upper bound, and the same shallow head using only direct
confidence/entropy/expert-disagreement inputs. Add semantic-only,
frequency-only and full-feature ablations to test whether those channels
actually contribute. The SGMA/CAF-Net family remains related work; this
minimal protocol does not claim to replicate either architecture.

## Leakage-proof source design

Before any fitting, accept a dataset under
`docs/current/INDEPENDENT_SOURCE_DECISION_20260923.md` and freeze four
spatially disjoint scene groups: expert training, benefit-head training,
threshold calibration, and final evaluation. R01/R05 must be matched and
trained only on the expert-training group; benefit labels must come from
their out-of-training-scene predictions. Do not put neighboring patches of
one original scene into different groups. If the dataset lacks sufficient
separate scenes, this experiment does not launch. Dataset-specific class
mapping and condition severity are fixed before seeing D10 evaluation.

Use two expert/head seeds. On fitting scenes, vary clean, complete/local
DSM absence, blur, downsampling, noise and shift without changing labels.
Known missingness comes from recorded masks or metadata. Neither an exact
zero fill nor a synthetic corruption label may be advertised as a learned
real-world missingness detector. RGB failure modes are a later extension,
required before any arbitrary-modality claim.

## Calibration and prespecified decision

Choose `tau` on calibration scenes to meet a selected-dual harm budget,
where harm is `selected & (t=-1)` and the denominator is selected
disagreement pixels. Report selection coverage as well, to prevent a
trivial always-RGB solution. The exact budget and minimum coverage must be
frozen with the accepted source, before final evaluation. No tuning on final
evaluation scenes or historical Potsdam Test6.

Report per-scene and pooled flip-benefit AUROC/AUPRC, calibration/ECE of
`p+` and `p-`, selected harm rate/count, selection coverage, FullGT and
NoBoundary mIoU, and per-class/object-size results. Treat scenes, not pixels,
as independent units. Report Car and Building separately where present;
if the external source lacks Car, do not claim small-Car validation.

Proceed to the residual model only if both seeds improve over the strongest
simple control on flip-benefit AUROC and AUPRC, selected harm falls at least
10% relative to safe confidence at nontrivial coverage, no severe DSM-noise
condition loses more than 0.3 pp NoBoundary mIoU, and Building/rare-class
effects are not hidden by the mean. Also apply the full D9 entry gate in
`docs/protocols/D9_DSM_BENEFIT_DIAGNOSTIC.md`; these checks cannot waive its
requirements. If either seed fails, retain D10 as a negative result and stop
the residual-fusion line.

All future runtime artifacts must stay under `/home/jovyan/zzx`; use only
physical GPU 0; each queue stage must fail independently and continue.
