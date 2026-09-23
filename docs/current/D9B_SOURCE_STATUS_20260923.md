# D9B independent-source audit — repository evidence only

The D9A entropy-route queue is running. This read-only audit identifies which
labelled scenes are already exposed in the repository; it does not inspect
the server's dataset files or load any image, DSM, label or historical TEST6
tile.

| Dataset | Documented scene IDs | Prior use | D9B status |
|---|---|---|---|
| Potsdam | Train16 in `configs/rebuild_v1/potsdam_split_seed20260915.json` | R01/R05 training | Cannot evaluate these frozen experts independently on their training scenes |
| Potsdam | `3_11`, `5_10` | Repeated Val2 model and method selection | Exploratory diagnostics only |
| Potsdam | `4_10`, `5_11`, `2_11`, `3_10`, `6_11`, `7_12` | Historically exposed TEST6 | Frozen; must not be loaded for D9 selection |
| Vaihingen | `1,3,7,11,13,17,23,26,28,32,34,37` | Earlier F0/P1 training | Not unseen evidence |
| Vaihingen | `5,15,21,30` | Earlier F0/P1 evaluation and comparison | Previously inspected; not an untouched final test |

Vaihingen scene IDs are specified in `scripts/train_vaihingen_formal.py` and
`records/DETPAIR_PREFUSION_FREQ_VAIHINGEN_FROZEN_20260831.md`. The known
Potsdam split covers all 24 documented scenes. No currently documented scene
set qualifies as an independent confirmatory D9B evaluation source. This
does **not** prove that the server has no other labelled scenes; their
availability and prior exposure still require a metadata-only inventory.

For D9B, first identify an additional labelled optical+DSM segmentation
scene set or genuinely unused labelled scenes, then freeze scene IDs and
fitting/calibration/evaluation partitions before extracting predictors.
Cross-dataset input bands, resolution, class mapping, DSM normalization and
missingness must be specified. If such a source is unavailable, keep
semantic/frequency benefit modelling as an exploratory protocol and do not
train a deployable safety gate or report an independent generalization claim.
