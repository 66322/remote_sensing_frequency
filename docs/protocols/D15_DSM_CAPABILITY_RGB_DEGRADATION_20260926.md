# D15: DSM capability and RGB degradation headroom (exploratory)

Status on 2026-09-26: runnable code committed after local checks; no server run has been observed. Two physical GPUs 0 and 1 are authorized for this D15 queue. The former GPU0-only execution boundary applies to older queues, not to this new queue. D15 uses one independent process per GPU, each seeing one logical `cuda:0`; it does not use distributed training.

## Question and controls

Test whether DSM provides useful information when RGB loses spatial detail. First train a DSM-only baseline for seeds 42 and 17 using the exact R01 R50+ViT-B/16 segmentation architecture, ImageNet initialization, Train16/Val2 split, 512-pixel patch, effective batch 16, AdamW and complete 16k schedule. The input is the existing R02 per-tile min-max normalized DSM repeated into three channels. This estimates capability under this pipeline, not an absolute DSM ceiling. Both runs select the best checkpoint on Val2 NoBoundary foreground-five mIoU. Test6 is never loaded.

Evaluate existing frozen R01, R05, and C-OO-QD best checkpoints for both seeds, and the newly trained DSM-only checkpoint. The condition list is frozen in `configs/rebuild_v1/d15_capability_20260926.json`: clean; RGB downsample/restore by 2 or 4; RGB blur5; a fixed center-quarter RGB down4 patch; and RGB down4 with DSM values set to zero. Downsample/restore uses antialiased bilinear reduction followed by bilinear enlargement. These synthetic perturbations test sensitivity; they do not establish real low-resolution generalization or constitute a trained SR model.

R01 receives only perturbed RGB. R05 receives perturbed RGB and original DSM except in the final zero-DSM diagnostic. C-OO-QD receives perturbed RGB and the grayscale mean of that **same perturbed RGB** in its second branch. DSM-only receives original DSM except in the final zero-DSM diagnostic, so its prediction should be RGB-condition invariant. All comparisons use identical Val2 tiles, labels, inference patch/stride and seeds.

Save each condition's int64 6x6 confusion matrices, class counts derivable from them, foreground-five and six-class metrics, per-tile results, paired R01-versus-candidate correctness counts, and the ground-truth-informed pixel oracle. The oracle is diagnostic and cannot be deployed. D4 already measured some R01/R05 complementarity under other conditions; this experiment does not present an old oracle as a new discovery. Count independent scenes/tiles, not millions of pixels, as units for generalization.

## Prespecified exploration screen

For the four RGB-only degradations, compute R05 NoBoundary foreground-five mIoU minus the better of R01 and C-OO-QD in each same-seed condition. Mark the **RGB degradation gate** true only if each seed has mean improvement of at least +0.2 percentage points and positive improvement in at least three of four conditions. This is a resource-allocation rule, not a significance test. Also inspect clean performance, each tile, Building/Tree/Car, harm/rescue, DSM-zero sensitivity, and DSM-only capability before choosing the next method. The queue does not launch a new-method training branch automatically.

If both-seed gains concentrate under RGB degradation, the next protocol should test DSM-guided feature recovery with matched RGB-only capacity and ordinary fusion controls. If gains are absent but paired expert oracle headroom is reproducible, consider a new harm/rescue-balanced mechanism with sham reweighting controls. If neither pattern is stable, reassess representation or data rather than tune D13/D14 thresholds. Val2 is repeatedly used exploratory data; an independent scene source is required before a confirmatory result. Historical Test6 remains frozen.

## Execution and continuation

Run from the server root and `remote_sensing` environment after pulling the committed branch:

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
conda activate remote_sensing
git pull --ff-only origin rebuild-v1-protocol-20260915
mkdir -p records/rebuild_v1_d15_capability_queue_20260926
nohup bash scripts/run_rebuild_v1_d15_capability_queue.sh > records/rebuild_v1_d15_capability_queue_20260926/launcher.log 2>&1 &
```

GPU0 runs a one-step train smoke, full DSM-only seed42, then its evaluation. GPU1 runs an inference smoke, full DSM-only seed17 and its evaluation, then six existing-model/seed evaluations. The two workers run concurrently. There is no one-day kill timer: checkpointed training continues past 24 hours. On interruption, rerun the same queue; completed summaries are reused and incomplete trainings with `last_train_state.pth` resume. It refuses ambiguous pre-checkpoint partial runs and invalid existing summaries rather than overwrite them.

Inspect `records/rebuild_v1_d15_capability_queue_20260926/status.tsv` and `summary.log`, then `records/rebuild_v1_d15_capability_20260926/decision.json`. `QUEUE FINISHED` alone is insufficient: require `status=COMPLETE`, empty `missing`, both worker exit codes zero, and inspect the gate and per-tile/class evidence. Server run status must be reported with the last observed time. Before cross-computer interpretation, archive compact summaries and checkpoint paths/hashes in GitHub; do not commit weights or full datasets.
