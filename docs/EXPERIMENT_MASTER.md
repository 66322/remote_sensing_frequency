# Remote Sensing Frequency Project — Experiment Master

> 本文件是本项目的实验总索引。
>
> 任何正式/筛选实验均应在此登记：
> 实验目的、数据集、模型代码、训练脚本、run目录、训练预算、
> 主要结果、结论、下一步以及对应 Git commit。
>
> 不再依赖文件名猜测实验含义。

---

# 1. 当前研究目标

任务：

- ISPRS 遥感语义分割
- Optical + DSM 双模态
- 重点研究：
  1. 融合前跨模态频率可靠性；
  2. 稀有类别采样；
  3. 难例历史采样；
  4. 浅层细节保持；
  5. 小目标与边界改善。

当前主线：

P2-H
→ Rare30
→ Shallow Detail Preservation

当前 10k 最优：

**E32 P2-H + Rare30**

Vaihingen NB:

- OA = 92.2850%
- mF1_fg5 = 90.4897%
- mIoU_fg5 = 83.0658%

当前正在验证：

- E40 NormalDetail
- E41 HFDetail

---

# 2. 数据集协议

## 2.1 Vaihingen

Train12:

1, 3, 7, 11, 13, 17, 23, 26, 28, 32, 34, 37

Test4:

5, 15, 21, 30

输入：

- Optical: IRRG
- DSM

类别：

0. Impervious
1. Building
2. LowVegetation
3. Tree
4. Car
5. Clutter/background

主要指标：

- NB / noBoundary
- OA
- mF1_fg5
- mIoU_fg5

同时保留：

- FullGT
- all6

---

## 2.2 Potsdam

Train18:

6_10, 7_10, 2_12, 3_11, 2_10, 7_8,
5_10, 3_12, 5_12, 7_11, 7_9, 6_9,
7_7, 4_12, 6_8, 6_12, 6_7, 4_11

Test6:

4_10, 5_11, 2_11, 3_10, 6_11, 7_12

---

# 3. 统一训练协议

当前筛选实验默认：

- seed = 42
- crop = 512 × 512
- random scale = 0.5–2.0
- physical batch = 4
- gradient accumulation = 4
- effective batch = 16
- optimizer = AdamW
- backbone LR = 6e-5
- decoder/head/new-module LR = 6e-4
- weight decay = 0.01
- warmup = 1500 optimizer steps
- evaluation interval = 2000 steps
- screening budget = 10000 steps
- GPU = CUDA_VISIBLE_DEVICES=0

主 checkpoint：

- highest NB OA

同时记录：

- best NB OA
- best NB mF1_fg5
- best NB mIoU_fg5

---

# 4. 实验编号规则

## E00–E09 Baseline

基础模型与原始复现。

## E10–E19 Decoder Frequency

Decoder-stage frequency experiments.

## E20–E29 Pre-fusion Frequency

融合前频率可靠性实验。

## E30–E39 Sampling / Context

Crop、Rare sampling、History sampling。

## E40–E49 Detail Preservation

浅层细节、高频细节、小目标增强。

---

# 5. 实验总表

| ID | Method | Dataset | Budget | NB mIoU | Status | Conclusion |
|---|---|---|---:|---:|---|---|
| E00 | F0 baseline | Vaihingen | 40k | 82.7268 best | Done | 基础对照 |
| E10 | Decoder F0 | Vaihingen | 40k | 82.6386 primary | Done | baseline |
| E13 | Decoder F3 | Vaihingen | 40k | 82.5477 best | Done | decoder frequency增益很小 |
| E20 | P1 pre-fusion DSM HF calibration | Vaihingen | 40k | 83.1941 best | Done | 融合前频率有效 |
| E21 | P2-H cross-modal HF reliability | Vaihingen | 20k | 83.1850 | Done | 跨模态可靠性有效 |
| E30 | P1 + crop256 | Vaihingen | ~3k | 73.1822@2k | Rejected | 当前模型需要512上下文 |
| E31 | P1 + Rare30 | Vaihingen | 10k | 82.8807 | Done | 强有效 |
| E32 | P2-H + Rare30 | Vaihingen | 10k | **83.0658** | Current Best | 当前主线 |
| E33 | P1 + History30 | Vaihingen | 10k | 82.0895 | Done | 有效但弱于Rare30 |
| E34 | P1 + Rare15 + History15 | Vaihingen | 10k | 82.2388 | Done | 未证明互补 |
| E40 | P2-H + Rare30 + NormalDetail | Vaihingen | 2k | 79.5690 | Running/Pending 10k | 2k正增益 |
| E41 | P2-H + Rare30 + HFDetail | Vaihingen | 2k | 79.2304 | Running/Pending 10k | 2k正增益但弱于Normal |

Reference:

P2-H + Rare30 @2k = 79.0518

---

# 6. E20 — P1 Pre-fusion Frequency Calibration

## Purpose

验证：

融合前对 DSM 高频进行校准是否比 decoder 后频率增强更有效。

## Model

model/vitcross_seg_modeling_prefusion_freq_detpair.py

## Trainer

scripts/train_vaihingen_P1_detpair.py

## Main run

runs/Thesis_Ch4_NoSR_DetPair_P1_Vaihingen_P1_seed42_formal160k

## Main result

Best NB mIoU:

83.1941% @ 34k

## Conclusion

通过。

融合前频率处理比 decoder-stage frequency fusion 更有价值。

---

# 7. E21 — P2-H Cross-modal HF Reliability

## Purpose

使用 Optical / DSM 高频差异估计模态可靠性。

约束：

wo + wd = 1

So = 2wo
Sd = 2wd

因此：

So + Sd = 2

## Model

model/vitcross_seg_modeling_hf_reliability_detpair.py

## Trainer

scripts/train_vaihingen_P2H_detpair.py

## Main run

runs/Thesis_Ch4_NoSR_DetPair_P2H_Vaihingen_P2H_seed42_formal160k

## Result

20k NB mIoU:

83.1850%

## Important observation

Car 对 DSM 高频表现出稳定偏好。

## Conclusion

通过。

保留为当前核心频率机制。

---

# 8. E31 — Rare30

## Purpose

提升：

- LowVegetation
- Tree
- Car

特别是 Car 小目标。

## Sampling

70% random

30% targeted

Rare classes:

- LowVeg: 25%
- Tree: 25%
- Car: 50%

## Trainer

scripts/train_vaihingen_P1_Rare30_screen_v2run.py

## Run

runs/Thesis_Ch4_NoSR_ScreenV2_Rare30_P1_Vaihingen_P1_seed42_formal160k

## Result @10k

NB:

- OA = 92.1140
- mF1 = 90.3785
- mIoU = 82.8807

Per-class IoU:

- Impervious = 87.4444
- Building = 94.9705
- LowVeg = 68.4467
- Tree = 84.2318
- Car = 79.3102
- Clutter = 24.4554

## Conclusion

通过。

Rare30 是目前最有效的 sampling strategy。

---

# 9. E32 — P2-H + Rare30

## Purpose

验证频率可靠性与 Rare sampling 是否可以叠加。

## Model

model/vitcross_seg_modeling_hf_reliability_detpair.py

## Trainer

scripts/train_vaihingen_P2H_Rare30_screen_v2run.py

## Run

runs/Thesis_Ch4_NoSR_ScreenV2_Rare30_P2H_Vaihingen_P2H_seed42_formal160k

## Result @10k

NB:

- OA = 92.2850
- mF1 = 90.4897
- mIoU = **83.0658**

Per-class IoU:

- Impervious = 87.7727
- Building = 95.1703
- LowVeg = 68.7736
- Tree = 84.5056
- Car = 79.1068
- Clutter = 0.0000

## Conclusion

当前 10k 最优。

当前正式主线 baseline。

---

# 10. E33 — History30

## Hypothesis

多次预测失败的空间区域可能具有持续难度。

如果增加这些区域的学习机会，模型可能进一步提升。

## Audit evidence

固定训练窗口：

- window = 512
- stride = 256
- total = 780

相邻 hard-score Spearman:

2k→4k: 0.7684
4k→6k: 0.8719
6k→8k: 0.9011
8k→10k: 0.9252

5/5 Top20 persistent windows:

66 / 780 = 8.46%

## Trainer

scripts/train_vaihingen_P1_History30_screen.py

## Result @10k

NB mIoU:

82.0895%

## Per-class observation

Compared with Rare30:

- Impervious: -0.4500
- Building: +0.0442
- LowVeg: +0.5184
- Tree: +0.3168
- Car: -4.3854
- Clutter: -13.8278

## Conclusion

History hypothesis is valid:

persistent hard regions exist and targeted training helps.

However:

History30 is clearly weaker than Rare30.

Main weakness:

Car decreases strongly.

Therefore History is NOT current mainline.

---

# 11. E34 — Rare15 + History15

## Purpose

Test complementarity:

Rare prior
+
model historical difficulty.

## Sampling

Before 2k:

70% Random + 30% Rare

After 2k:

70% Random
15% Rare
15% History

## Result @10k

NB mIoU:

82.2388%

## Conclusion

Better than History30 but clearly below Rare30.

Strong complementarity is NOT demonstrated.

Stop this branch.

---

# 12. E40 — NormalDetail

## Full name

P2-H + Rare30 + Normal Shallow Detail Residual

## Purpose

Test whether preserving the shallow fused representation directly to
the final prediction stage benefits small objects and boundaries.

## Model

model/vitcross_seg_modeling_shallow_detail.py

detail_mode:

NORMAL

## Trainer

scripts/train_vaihingen_P2H_Rare30_NormalDetail_screen.py

## Run

runs/Thesis_Ch4_NoSR_ScreenV4_Rare30_P2H_NormalDetail_Vaihingen_P2H_seed42_formal160k

## Structure

Source:

features[-1]

64 channels @ input/2

after:

P2-H calibration
+
SE0 fusion

Projection:

64 → 16

1×1 Conv

zero initialization.

Injection:

decoder final output
+
detail residual
→ segmentation head

Extra parameters:

1040

## Step-0 gate

PASS

- common parameter mismatch = 0
- max output difference = 0
- initial detail residual = 0

## Result @2k

NB:

- OA = 91.4481
- mF1 = 88.2086
- mIoU = 79.5690

Compared with E32 @2k:

+0.5172 pp mIoU

## Status

Continue to 10k.

---

# 13. E41 — HFDetail

## Full name

P2-H + Rare30 + High-frequency Shallow Detail Residual

## Difference from E40

Only detail source changes:

NORMAL:

F_s

HF:

H_s = F_s - AvgPool3x3(F_s)

Everything else is identical.

## Model

model/vitcross_seg_modeling_shallow_detail.py

detail_mode:

HF

## Trainer

scripts/train_vaihingen_P2H_Rare30_HFDetail_screen.py

## Run

runs/Thesis_Ch4_NoSR_ScreenV4_Rare30_P2H_HFDetail_Vaihingen_P2H_seed42_formal160k

## Result @2k

NB:

- OA = 91.3268
- mF1 = 87.9698
- mIoU = 79.2304

Compared with E32 @2k:

+0.1786 pp

Compared with E40:

-0.3386 pp

## Current interpretation

Shallow detail preservation appears useful.

Pure HF-only detail is currently weaker than preserving the complete
shallow representation.

## Status

Continue to 10k.

---

# 14. 当前路线决策

Current best:

E32 P2-H + Rare30

NB mIoU @10k:

83.0658%

Current experiments:

E40 NormalDetail → 10k
E41 HFDetail → 10k

Decision after 10k:

Case A:

E40 > E41 > E32

Interpretation:

general shallow detail preservation helps more than HF-only detail.

Case B:

E41 > E40 > E32

Interpretation:

high-frequency-selective detail preservation is specifically useful.

Case C:

E40 ≈ E41 > E32

Interpretation:

gain mainly comes from additional shallow information.

Case D:

both ≤ E32

Stop detail branch.

---

# 15. 下一阶段候选

Only after E40/E41 10k finish.

Priority order:

1. Determine whether NormalDetail or HFDetail is retained.
2. Inspect Car / LowVeg / Tree per-class IoU.
3. If detail branch succeeds:
   test with Potsdam.
4. If detail branch fails:
   stop structural stacking.
5. Formal cross-dataset validation.
6. Re-run final selected model under locked protocol.
7. Generate final ablation table and qualitative examples.

No further History ratio search.

---

# 16. 文件命名规范

## New model files

Format:

model/exp_<ID>_<short_name>.py

Example:

model/exp_E42_detail_gate.py

## New training scripts

Format:

scripts/train_<ID>_<dataset>_<short_name>.py

Example:

scripts/train_E42_vaihingen_detail_gate.py

## New run directories

Format:

runs/<ID>_<dataset>_<method>_seed<seed>_<budget>

Example:

runs/E42_vaihingen_detail_gate_seed42_10k

## New analysis scripts

Format:

scripts/analyze_<ID>_<purpose>.py

Example:

scripts/analyze_E40_E41_per_class.py

---

# 17. Git规则

Every experiment should record:

- Experiment ID
- model file
- trainer file
- dataset
- seed
- crop
- training budget
- run directory
- main result
- conclusion
- Git commit SHA

Do NOT commit:

- *.pth
- *.pt
- *.npz
- raw dataset
- large predictions
- resume states

Keep:

- source code
- metrics CSV
- best_registry.json
- diagnostic CSV
- audit summary
- experiment documentation

---

# 18. Git Commit Mapping

| Experiment | Commit | Notes |
|---|---|---|
| Initial repository | TBD | Initial code and experiment archive |
| E32 P2-H + Rare30 | TBD | Current strongest completed screen |
| E40/E41 Detail | TBD | Current active experiments |

Update this table after every meaningful commit.

---

# 19. Current status

Last updated:

2026-09-11

Mainline:

E32 P2-H + Rare30

Current best:

83.0658% NB mIoU @10k

Active:

- E40 NormalDetail
- E41 HFDetail

Deprecated / stopped:

- decoder-only frequency enhancement as main innovation
- C256
- History ratio search
- Rare15History15
