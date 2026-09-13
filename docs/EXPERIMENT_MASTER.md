# Optical–DSM 双模态频率引导语义分割：实验总计划与完整记录

> 本文件是本项目唯一的实验主记录。
>
> 以后查看一个实验时，应当能够直接从本文件找到：
> 为什么做、与哪个实验比较、改了什么、数据在哪里、代码在哪里、
> 权重在哪里、运行结果在哪里、最终结果是多少、结论是什么、下一步做什么。
>
> P1、P2H、F0、ScreenV2、ScreenV3 等名称只作为历史文件定位名称，
> 不再作为实验的主要名称。

---

## 1. 当前项目状态

### 1.1 当前研究主线

本项目研究 Optical + DSM 双模态遥感语义分割。

当前主要问题包括：

- 提高 Optical 与 DSM 融合时的模态可靠性；
- 改善 LowVegetation / Tree 等易混类别与边界；
- 改善 Car 等小目标和稀有类别；
- 判断频率信息在哪个阶段使用最有效。

目前已经完成的研究路线为：

**NoSR 双模态基线**

↓

**Decoder 频率增强**

结果：存在小幅增益，但提升有限，因此不作为后续主线。

↓

**将频率建模前置到双模态融合之前**

↓

**DSM 高频校准**

结果：有效。

↓

**Optical/DSM 跨模态高频可靠性**

结果：有效，保留。

↓

**Rare30 稀有类别定向采样**

结果：进一步提高性能。

↓

**History 难例采样**

结果：不能超过 Rare30，停止。

↓

**浅层细节保持**

Normal Shallow Detail 与 HF Shallow Detail 均完成 10k 验证。

两者虽然能够改善早期收敛，
但最终 NB mIoU_fg5 均低于不加 Detail 的主基线，因此停止。

当前保留的统一 10k 主线为：

**Optical/DSM 跨模态高频可靠性 + Rare30**

Vaihingen 10k：

- NB OA = 92.2850
- NB mF1_fg5 = 90.4897
- NB mIoU_fg5 = **83.0658**

### 1.2 当前最好已完成实验

#### Vaihingen｜Optical/DSM 跨模态高频可靠性 + Rare30

训练预算：10k steps。

这是目前统一 10k 筛选实验中的最佳方案，也是后续研究的主基线。

| 指标 | 结果 |
|---|---:|
| NB OA | 92.2850 |
| NB mF1_fg5 | 90.4897 |
| NB mIoU_fg5 | **83.0658** |

NB 各类 IoU：

| 类别 | IoU |
|---|---:|
| Impervious | 87.7727 |
| Building | 95.1703 |
| LowVegetation | 68.7736 |
| Tree | 84.5056 |
| Car | 79.1068 |
| Clutter | 0.0000 |

当前状态：

**CURRENT MAIN BASELINE**

### 1.3 当前正在运行的实验

当前没有需要继续训练的浅层 Detail 实验。

Normal Shallow Detail 与 HF Shallow Detail 均已完成 10k，
并确认不能超过当前主基线。

下一轮结构实验开始前，先以：

**Optical/DSM 跨模态高频可靠性 + Rare30**

作为统一对照。

### 1.4 最近下一步

当前不继续 Normal Shallow Detail 或 HF Shallow Detail。

当前主基线：

**Optical/DSM 跨模态高频可靠性 + Rare30**

10k NB mIoU_fg5：

**83.0658**

下一阶段研究应优先针对现有薄弱类别，
特别是 Car 小目标以及 LowVegetation / Tree 的类别与边界问题。

浅层 Detail 实验说明：

简单地在最终预测前重复注入浅层特征，
即使能够改善早期收敛，也不能保证最终性能提高。

HF Shallow Detail 还表现出非常明显的类别重分配现象：
Clutter 大幅提高，但 Car 明显下降。

因此后续不继续做简单浅层残差叠加。

## 2. 公共路径、数据、权重和评价设置

### 2.1 项目根目录

服务器：

`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro`

GitHub：

`66322/remote_sensing_frequency`

---

### 2.2 公共预训练权重

R50 + ViT-B/16：

`/home/jovyan/zzx/paper_rebuild/08_assets/pretrained/ftransunet/R50+ViT-B_16.npz`

说明：

该权重不上传 GitHub。

GitHub 只保存代码、路径以及实验记录。

---

### 2.3 Vaihingen 数据

数据根目录：

`/home/jovyan/zzx/projects_zys/raw_extract/Vaihingen`

NoBoundary / eroded GT：

`/home/jovyan/zzx/projects_zys/ISPRS_dataset/Vaihingen/gts_eroded_for_participants`

输入：

- Optical IRRG
- DSM

Train tiles：

`1, 3, 7, 11, 13, 17, 23, 26, 28, 32, 34, 37`

Test tiles：

`5, 15, 21, 30`

空间分辨率：

约 9 cm。

---

### 2.4 Potsdam 数据

数据根目录：

`/home/jovyan/zzx/projects_zys/raw_extract/Potsdam_unzipped`

RGB：

`/home/jovyan/zzx/projects_zys/raw_extract/Potsdam_unzipped/2_Ortho_RGB`

DSM：

`/home/jovyan/zzx/projects_zys/raw_extract/Potsdam_unzipped/1_DSM/1_DSM`

Full GT：

`/home/jovyan/zzx/projects_zys/raw_extract/Potsdam_unzipped/5_Labels_for_participants`

NoBoundary GT：

`/home/jovyan/zzx/projects_zys/raw_extract/Potsdam_unzipped/5_Labels_for_participants_no_Boundary`

Train tiles：

`6_10, 7_10, 2_12, 3_11, 2_10, 7_8, 5_10, 3_12, 5_12, 7_11, 7_9, 6_9, 7_7, 4_12, 6_8, 6_12, 6_7, 4_11`

Test tiles：

`4_10, 5_11, 2_11, 3_10, 6_11, 7_12`

空间分辨率：

约 5 cm。

---

### 2.5 类别

统一 6 类：

1. Impervious surface
2. Building
3. Low vegetation
4. Tree
5. Car
6. Clutter / Background

主要论文指标使用前五个前景类别：

`fg5`

同时保留：

`all6`

---

### 2.6 评价

同时计算：

- FullGT
- NoBoundary / eroded GT

主要比较优先查看：

- NB OA
- NB mF1_fg5
- NB mIoU_fg5

同时累计完整 6 × 6 confusion matrix。

---

### 2.7 常用统一设置

随机种子：

`42`

主要快速筛选 crop：

`512 × 512`

当前不再采用 crop 256 作为主设置。

GPU：

仅使用 `CUDA_VISIBLE_DEVICES=0`

确定性相关设置：

`PYTHONHASHSEED=42`

`CUBLAS_WORKSPACE_CONFIG=:4096:8`

---

## 3. 总实验计划与研究逻辑

### 3.1 建立双模态 NoSR 基线

要回答的问题：

**不使用 SR，仅使用 Optical + DSM 双模态网络，本身能够达到什么水平？**

作用：

后续所有结构实验必须有统一基准。

状态：

COMPLETED。

---

### 3.2 验证 Decoder 频率增强

要回答的问题：

**频率增强放在 decoder 阶段是否能够明显提高分割性能？**

逐步加入：

F0：普通上采样基线

F1：LFAU

F2：LFAU + SGOR

F3：LFAU + SGOR + HFDC

主要结论：

Vaihingen 和 Potsdam 都观察到一定增益，但提升幅度有限。

Potsdam F0 → F3：

约 **+0.2674 mIoU**

Vaihingen 的增益更小。

结论：

**Decoder 后期频率增强不作为后续主要创新方向。**

状态：

STOPPED AS MAIN LINE。

---

### 3.3 将频率前置到融合之前

新的问题：

**频率信息是否应该在 Optical 与 DSM 融合之前发挥作用，而不是只在 decoder 后端修补？**

第一步使用 DSM-only 高频校准进行验证。

结果明显优于单纯 decoder 频率增强。

因此频率前置成为后续主线。

---

### 3.4 Optical/DSM 跨模态高频可靠性

进一步的问题：

**能否利用 Optical 与 DSM 高频差异动态判断哪个模态在当前位置更可靠？**

由 DSM-only 校准升级为：

**Cross-modal HF Reliability**

即根据 Optical / DSM 高频差异预测互补的空间模态可靠性。

结果有效。

状态：

保留。

---

### 3.5 Rare30 稀有类别采样

问题：

**Car 等类别是否因为普通随机 crop 中出现频率不足而限制性能？**

方案：

70% 普通随机 crop。

30% 稀有类别定向 crop。

Rare30 内部目标权重：

LowVegetation：0.25

Tree：0.25

Car：0.50

结果：

在 Cross-modal HF Reliability 基础上继续提升。

当前成为后续结构筛选的主要基线。

---

### 3.6 History 难例采样

问题：

**历史上模型长期分错的空间区域，是否比 Rare 类别采样更值得重复学习？**

验证：

History30

以及：

Rare15 + History15

结果：

两者均未超过 Rare30。

其中 History 对 LowVegetation / Tree 部分指标有帮助，
但明显伤害 Car。

结论：

不继续进行 History 比例搜索。

状态：

STOPPED。

---

### 3.7 浅层细节保持

研究问题：

在已经使用 Optical/DSM 跨模态高频可靠性和 Rare30 后，
最终预测前再次加强浅层结构信息是否还能提高边界和小目标性能？

进行了两个严格控制实验：

**Normal Shallow Detail**

直接注入完整浅层融合特征。

**HF Shallow Detail**

仅注入浅层高频残差：

`F_s - AvgPool3×3(F_s)`

两者使用：

- 相同浅层特征来源；
- 相同注入位置；
- 相同 64→16 projection；
- 相同新增参数量 1040；
- 相同 zero-init endpoint。

10k NB mIoU_fg5：

| 实验 | NB mIoU_fg5 |
|---|---:|
| 跨模态高频可靠性 + Rare30 | **83.0658** |
| + Normal Shallow Detail | 82.4473 |
| + HF Shallow Detail | 82.4446 |

相对主基线：

- Normal Detail：-0.6185
- HF Detail：-0.6212

两种 Detail 均只能改善早期训练表现，
不能改善统一 10k 预算下的最终 fg5 性能。

其中 HF Detail 出现明显的类别性能重新分配：

- LowVegetation：+0.0229 IoU
- Tree：-0.0152 IoU
- Car：-2.6506 IoU
- Clutter：+67.3141 IoU

因此：

**Normal Shallow Detail：REJECTED**

**HF Shallow Detail：REJECTED / DIAGNOSTICALLY INTERESTING**

不继续进行 20k / 40k 扩展实验。

## 4. 详细实验记录

### 4.1 Vaihingen｜确定性双模态基线

#### 实验目的

建立融合前频率实验使用的严格确定性基线。

历史名称：

`F0 / DetPair F0`

历史名称只用于定位旧文件。

---

#### 数据

使用第 2.3 节 Vaihingen 数据。

---

#### 主要代码

训练脚本：

`scripts/train_vaihingen_F0_detpair.py`

相关评估：

`scripts/evaluate_detpair_F0_per_class.py`

---

#### 公共预训练权重

`/home/jovyan/zzx/paper_rebuild/08_assets/pretrained/ftransunet/R50+ViT-B_16.npz`

---

#### 运行目录

`runs/Thesis_Ch4_NoSR_DetPair_F0_Vaihingen_F0_seed42_formal160k`

---

#### 权重

保存的关键 checkpoint：

`runs/Thesis_Ch4_NoSR_DetPair_F0_Vaihingen_F0_seed42_formal160k/checkpoints/model_iter_014000.pth`

`runs/Thesis_Ch4_NoSR_DetPair_F0_Vaihingen_F0_seed42_formal160k/checkpoints/model_iter_034000.pth`

恢复训练状态：

`runs/Thesis_Ch4_NoSR_DetPair_F0_Vaihingen_F0_seed42_formal160k/last_train_state.pth`

---

#### 结果文件

`runs/Thesis_Ch4_NoSR_DetPair_F0_Vaihingen_F0_seed42_formal160k/best_registry.json`

`runs/Thesis_Ch4_NoSR_DetPair_F0_Vaihingen_F0_seed42_formal160k/metrics_history.csv`

---

#### 关键结果

40k 范围内最佳 NB mIoU_fg5：

**82.7268**

---

#### 结论

作为确定性融合前频率实验的主要基础对照。

状态：

COMPLETED。

---

### 4.2 Vaihingen / Potsdam｜Decoder 频率增强消融

#### 实验目的

验证频率模块放在 decoder 端是否能够稳定带来明显提升。

---

#### 变量

F0：

普通 bilinear / 无完整频率增强。

F1：

LFAU。

F2：

LFAU + SGOR。

F3：

LFAU + SGOR + HFDC。

---

#### 主要代码

Vaihingen：

`scripts/train_vaihingen_freq_ablation.py`

Potsdam：

`scripts/train_potsdam_freq_ablation.py`

相关模型文件：

`model/vitcross_seg_modeling_freq_ablation.py`

`model/vitcross_seg_modeling_freqfusion.py`

---

#### Vaihingen 运行目录

`runs/Thesis_Ch4_NoSR_Ablation_Vaihingen_F0_seed42`

`runs/Thesis_Ch4_NoSR_Ablation_Vaihingen_F1_seed42`

`runs/Thesis_Ch4_NoSR_Ablation_Vaihingen_F2_seed42`

---

#### Potsdam 运行目录

`runs/Thesis_Ch4_NoSR_Ablation_Potsdam_F0_seed42`

`runs/Thesis_Ch4_NoSR_Ablation_Potsdam_F1_seed42`

`runs/Thesis_Ch4_NoSR_Ablation_Potsdam_F2_seed42`

`runs/Thesis_Ch4_NoSR_Ablation_Potsdam_F3_seed42`

---

#### 结果文件

每个目录均保存：

`best_registry.json`

`final_summary.json`

`metrics_history.csv`

---

#### 结论

Decoder 频率增强有一定作用，但没有形成足够大的稳定优势。

因此：

**不继续在 decoder 后端不断叠加频率模块。**

后续转向融合前频率建模。

状态：

COMPLETED / MAIN LINE STOPPED。

---

### 4.3 Vaihingen｜融合前 DSM 高频校准

#### 实验目的

验证频率信息在双模态融合前使用是否比 decoder 后端使用更有效。

---

#### 核心变化

仅利用 DSM 高频信息进行融合前校准。

历史名称：

`P1`

---

#### 模型代码

`model/vitcross_seg_modeling_prefusion_freq_detpair.py`

---

#### 训练代码

`scripts/train_vaihingen_P1_detpair.py`

---

#### 审计代码

`scripts/audit_detpair_P1_2k_scale_by_class.py`

`scripts/audit_detpair_P1_34k_scale_by_class.py`

`scripts/analyze_detpair_F0_P1_40k.py`

---

#### 运行目录

`runs/Thesis_Ch4_NoSR_DetPair_P1_Vaihingen_P1_seed42_formal160k`

---

#### 权重

最佳关键 checkpoint：

`runs/Thesis_Ch4_NoSR_DetPair_P1_Vaihingen_P1_seed42_formal160k/checkpoints/model_iter_034000.pth`

恢复状态：

`runs/Thesis_Ch4_NoSR_DetPair_P1_Vaihingen_P1_seed42_formal160k/last_train_state.pth`

---

#### 结果文件

`runs/Thesis_Ch4_NoSR_DetPair_P1_Vaihingen_P1_seed42_formal160k/best_registry.json`

`runs/Thesis_Ch4_NoSR_DetPair_P1_Vaihingen_P1_seed42_formal160k/metrics_history.csv`

---

#### 结果

2k：

NB mIoU_fg5 = **78.0476**

同 step F0：

77.4944

提升：

**+0.5532**

40k 范围最佳：

NB mIoU_fg5 = **83.1941 @ 34k**

F0 对应最佳：

82.7268

提升：

**+0.4673**

---

#### 结论

融合前频率校准比继续在 decoder 后端堆叠频率模块更有研究价值。

状态：

COMPLETED / EFFECTIVE。

---

### 4.4 Vaihingen｜Optical/DSM 跨模态高频可靠性

#### 实验目的

从 DSM-only 高频校准进一步升级。

利用 Optical 与 DSM 高频差异动态估计模态可靠性。

历史名称：

`P2H`

以后正式记录中不再使用 P2H 作为实验主名称。

---

#### 模型代码

`model/vitcross_seg_modeling_hf_reliability_detpair.py`

---

#### 训练代码

`scripts/train_vaihingen_P2H_detpair.py`

---

#### 审计代码

`scripts/audit_detpair_P2H_2k_reliability_by_class.py`

`scripts/audit_detpair_P2H_20k_reliability_by_class.py`

`scripts/check_P2H_detpair_seed_fairness.py`

---

#### 运行目录

`runs/Thesis_Ch4_NoSR_DetPair_P2H_Vaihingen_P2H_seed42_formal160k`

---

#### 权重

20k checkpoint：

`runs/Thesis_Ch4_NoSR_DetPair_P2H_Vaihingen_P2H_seed42_formal160k/checkpoints/model_iter_020000.pth`

恢复状态：

`runs/Thesis_Ch4_NoSR_DetPair_P2H_Vaihingen_P2H_seed42_formal160k/last_train_state.pth`

---

#### 结果文件

`runs/Thesis_Ch4_NoSR_DetPair_P2H_Vaihingen_P2H_seed42_formal160k/best_registry.json`

`runs/Thesis_Ch4_NoSR_DetPair_P2H_Vaihingen_P2H_seed42_formal160k/metrics_history.csv`

`runs/Thesis_Ch4_NoSR_DetPair_P2H_Vaihingen_P2H_seed42_formal160k/p2h_diagnostics.csv`

---

#### 结果

2k：

NB mIoU_fg5 = **78.6107**

20k：

NB mIoU_fg5 = **83.1850**

20k per-class IoU：

| 类别 | IoU |
|---|---:|
| Impervious | 87.5243 |
| Building | 95.2395 |
| LowVegetation | 69.1190 |
| Tree | 84.2977 |
| Car | 79.7446 |

---

#### 可靠性分析

20k 平均 Optical / DSM 权重：

| 类别 | Optical | DSM |
|---|---:|---:|
| Impervious | 0.5727 | 0.4273 |
| Building | 0.5387 | 0.4613 |
| LowVegetation | 0.5388 | 0.4612 |
| Tree | 0.4992 | 0.5008 |
| Car | 0.4752 | 0.5248 |

Car 对 DSM 高频表现出更明显的偏好。

---

#### 结论

跨模态高频可靠性建模有效。

后续不继续跑 40k，而是进入统一 10k 快速组合验证。

状态：

COMPLETED / RETAINED。

---

### 4.5 Vaihingen｜DSM 高频校准 + Rare30

#### 实验目的

先验证 Rare30 采样本身是否能够在融合前频率模型上产生增益。

历史名称：

`P1 + Rare30`

---

#### 模型

`model/vitcross_seg_modeling_prefusion_freq_detpair.py`

---

#### 训练代码

`scripts/train_vaihingen_P1_Rare30_screen_v2run.py`

---

#### 运行目录

`runs/Thesis_Ch4_NoSR_ScreenV2_Rare30_P1_Vaihingen_P1_seed42_formal160k`

---

#### 权重

10k checkpoint：

`runs/Thesis_Ch4_NoSR_ScreenV2_Rare30_P1_Vaihingen_P1_seed42_formal160k/checkpoints/model_iter_010000.pth`

恢复状态：

`runs/Thesis_Ch4_NoSR_ScreenV2_Rare30_P1_Vaihingen_P1_seed42_formal160k/last_train_state.pth`

---

#### 结果文件

`runs/Thesis_Ch4_NoSR_ScreenV2_Rare30_P1_Vaihingen_P1_seed42_formal160k/best_registry.json`

`runs/Thesis_Ch4_NoSR_ScreenV2_Rare30_P1_Vaihingen_P1_seed42_formal160k/metrics_history.csv`

---

#### 结果

10k：

NB OA = **92.1140**

NB mF1_fg5 = **90.3785**

NB mIoU_fg5 = **82.8807**

---

#### 结论

Rare30 有效。

下一步与更强的 Cross-modal HF Reliability 组合。

状态：

COMPLETED。

---

### 4.6 Vaihingen｜跨模态高频可靠性 + Rare30

#### 实验目的

将当前最有效的网络侧改动：

**Cross-modal HF Reliability**

与训练采样侧改动：

**Rare30**

组合。

---

#### 唯一新增采样策略

70%：

普通随机 crop。

30%：

稀有类别定向 crop。

目标类别权重：

LowVegetation = 0.25

Tree = 0.25

Car = 0.50

---

#### 模型代码

`model/vitcross_seg_modeling_hf_reliability_detpair.py`

---

#### 训练代码

`scripts/train_vaihingen_P2H_Rare30_screen_v2run.py`

---

#### 运行目录

`runs/Thesis_Ch4_NoSR_ScreenV2_Rare30_P2H_Vaihingen_P2H_seed42_formal160k`

---

#### 权重

10k checkpoint：

`runs/Thesis_Ch4_NoSR_ScreenV2_Rare30_P2H_Vaihingen_P2H_seed42_formal160k/checkpoints/model_iter_010000.pth`

恢复状态：

`runs/Thesis_Ch4_NoSR_ScreenV2_Rare30_P2H_Vaihingen_P2H_seed42_formal160k/last_train_state.pth`

---

#### 结果文件

`runs/Thesis_Ch4_NoSR_ScreenV2_Rare30_P2H_Vaihingen_P2H_seed42_formal160k/best_registry.json`

`runs/Thesis_Ch4_NoSR_ScreenV2_Rare30_P2H_Vaihingen_P2H_seed42_formal160k/metrics_history.csv`

`runs/Thesis_Ch4_NoSR_ScreenV2_Rare30_P2H_Vaihingen_P2H_seed42_formal160k/p2h_diagnostics.csv`

---

#### 结果

2k：

NB mIoU_fg5 = **79.0518**

10k：

NB OA = **92.2850**

NB mF1_fg5 = **90.4897**

NB mIoU_fg5 = **83.0658**

per-class IoU：

| 类别 | IoU |
|---|---:|
| Impervious | 87.7727 |
| Building | 95.1703 |
| LowVegetation | 68.7736 |
| Tree | 84.5056 |
| Car | 79.1068 |

---

#### 结论

当前已完成的统一 10k 实验中最佳。

后续浅层结构实验统一以此为主基线。

状态：

**CURRENT MAIN BASELINE**

---

### 4.7 Vaihingen｜Crop 256 验证

#### 实验目的

判断减小 crop 是否能够增加训练样本变化，并提高性能。

历史名称：

`P1 + C256`

---

#### 训练代码

`scripts/train_vaihingen_P1_C256_screen_v2run.py`

---

#### 运行目录

`runs/Thesis_Ch4_NoSR_ScreenV2_C256_P1_Vaihingen_P1_seed42_formal160k`

---

#### 结果

2k NB mIoU_fg5：

**73.1822**

对应 512 crop：

78.0476

---

#### 结论

性能明显下降。

说明当前模型需要较大的上下文。

**后续统一保持 crop 512。**

状态：

REJECTED。

---

### 4.8 Vaihingen｜History30 历史难例采样

#### 实验目的

验证长期被模型分错的空间区域是否值得优先重复采样。

---

#### 历史区域审计

固定 512 window。

Stride：

256。

Train12 共：

780 个 window。

观察：

2k / 4k / 6k / 8k / 10k。

困难区域在训练过程中具有较强持续性。

---

#### 训练代码

`scripts/train_vaihingen_P1_History30_screen.py`

历史审计：

`scripts/build_P1_history_audit_20260910.py`

---

#### 运行目录

`runs/Thesis_Ch4_NoSR_ScreenV3_History30_P1_Vaihingen_P1_seed42_formal160k`

---

#### 权重

10k checkpoint：

`runs/Thesis_Ch4_NoSR_ScreenV3_History30_P1_Vaihingen_P1_seed42_formal160k/checkpoints/model_iter_010000.pth`

恢复状态：

`runs/Thesis_Ch4_NoSR_ScreenV3_History30_P1_Vaihingen_P1_seed42_formal160k/last_train_state.pth`

---

#### 结果

10k NB mIoU_fg5：

**82.0895**

---

#### 结论

困难区域确实具有持续性，因此分析本身有价值。

但作为训练采样策略：

**弱于 Rare30。**

尤其 Car 明显下降。

不继续搜索 History30 比例。

状态：

STOPPED。

---

### 4.9 Vaihingen｜Rare15 + History15

#### 实验目的

判断 Rare sampling 与 History hard-region sampling 是否具有互补性。

---

#### 训练代码

`scripts/train_vaihingen_P1_Rare15History15_screen.py`

---

#### 运行目录

`runs/Thesis_Ch4_NoSR_ScreenV3_Rare15History15_P1_Vaihingen_P1_seed42_formal160k`

---

#### 权重

10k checkpoint：

`runs/Thesis_Ch4_NoSR_ScreenV3_Rare15History15_P1_Vaihingen_P1_seed42_formal160k/checkpoints/model_iter_010000.pth`

恢复状态：

`runs/Thesis_Ch4_NoSR_ScreenV3_Rare15History15_P1_Vaihingen_P1_seed42_formal160k/last_train_state.pth`

---

#### 结果

10k NB mIoU_fg5：

**82.2388**

---

#### 结论

没有超过 Rare30。

没有证明二者存在值得继续搜索的明显互补性。

状态：

STOPPED。

---

### 4.10 Vaihingen｜跨模态高频可靠性 + Rare30 + 完整浅层细节保持

#### 状态

**REJECTED**

训练已完成至 10k。

---

#### 实验目的

验证在当前主基线已经包含：

- Optical/DSM 跨模态高频可靠性
- Rare30

之后，在最终预测前再次加入完整浅层融合特征，
是否能够进一步改善边界和小目标。

历史名称：

`P2H + Rare30 + NormalDetail`

---

#### 对照实验

Vaihingen｜Optical/DSM 跨模态高频可靠性 + Rare30。

对照实验 10k：

NB mIoU_fg5 = **83.0658**

---

#### 本实验唯一结构变化

浅层融合特征记为：

`F_s`

直接保留完整浅层信息：

`F_detail = F_s`

使用：

`1×1 Conv, 64 → 16`

新增参数：

1040。

projection endpoint 使用 zero initialization，
因此 step 0 与原主基线完全一致。

---

#### 模型代码

`model/vitcross_seg_modeling_shallow_detail.py`

---

#### 训练代码

`scripts/train_vaihingen_P2H_Rare30_NormalDetail_screen.py`

---

#### 公共预训练权重

`/home/jovyan/zzx/paper_rebuild/08_assets/pretrained/ftransunet/R50+ViT-B_16.npz`

---

#### 运行目录

`runs/Thesis_Ch4_NoSR_ScreenV4_Rare30_P2H_NormalDetail_Vaihingen_P2H_seed42_formal160k`

---

#### 最终 checkpoint

`runs/Thesis_Ch4_NoSR_ScreenV4_Rare30_P2H_NormalDetail_Vaihingen_P2H_seed42_formal160k/checkpoints/model_iter_010000.pth`

恢复状态：

`runs/Thesis_Ch4_NoSR_ScreenV4_Rare30_P2H_NormalDetail_Vaihingen_P2H_seed42_formal160k/last_train_state.pth`

---

#### 结果文件

`runs/Thesis_Ch4_NoSR_ScreenV4_Rare30_P2H_NormalDetail_Vaihingen_P2H_seed42_formal160k/best_registry.json`

`runs/Thesis_Ch4_NoSR_ScreenV4_Rare30_P2H_NormalDetail_Vaihingen_P2H_seed42_formal160k/metrics_history.csv`

`runs/Thesis_Ch4_NoSR_ScreenV4_Rare30_P2H_NormalDetail_Vaihingen_P2H_seed42_formal160k/p2h_diagnostics.csv`

---

#### 训练曲线

| Step | NB OA | NB mF1_fg5 | NB mIoU_fg5 |
|---:|---:|---:|---:|
| 2k | 91.4481 | 88.2086 | 79.5690 |
| 4k | 91.9332 | 89.3238 | 81.2339 |
| 6k | 91.8342 | 89.4530 | 81.4231 |
| 8k | 92.0910 | 89.9033 | 82.1156 |
| 10k | 92.0741 | 90.1027 | **82.4473** |

早期 2k 相比主基线同 step：

**+0.5172 mIoU**

但 10k：

**82.4473 vs 83.0658**

最终：

**-0.6185 mIoU**

---

#### 10k NB 各类结果

| 类别 | F1 | IoU | 相对主基线 IoU |
|---|---:|---:|---:|
| Impervious | 93.2229 | 87.3061 | -0.4666 |
| Building | 97.4585 | 95.0429 | -0.1273 |
| LowVegetation | 81.1372 | 68.2613 | -0.5123 |
| Tree | 91.4797 | 84.2973 | -0.2083 |
| Car | 87.2153 | 77.3290 | **-1.7778** |
| Clutter | 7.4807 | 3.8857 | +3.8857 |

---

#### FullGT 10k

OA = 88.9683

mF1_fg5 = 86.2917

mIoU_fg5 = 76.5024

主基线 FullGT mIoU_fg5：

76.9410

下降：

**-0.4386**

---

#### 结论

完整浅层细节保持只能改善早期训练阶段的收敛表现。

随着训练继续，主基线从 6k 开始重新反超，
10k 时差距扩大到 -0.6185 mIoU。

五个前景类别全部下降，
其中 Car 下降最明显。

因此：

**完整浅层细节保持不进入最终方法。**

不继续进行 20k / 40k 扩展实验。

### 4.11 Vaihingen｜跨模态高频可靠性 + Rare30 + 高频浅层细节保持

#### 状态

**REJECTED / DIAGNOSTICALLY INTERESTING**

训练已完成至 10k。

---

#### 实验目的

与完整浅层细节保持形成严格控制实验。

只使用浅层高频成分，而不是完整浅层特征。

---

#### 对照实验

Vaihingen｜Optical/DSM 跨模态高频可靠性 + Rare30。

对照实验 10k：

NB mIoU_fg5 = **83.0658**

---

#### 本实验唯一结构变化

浅层融合特征：

`F_s`

只保留高频残差：

`F_detail = F_s - AvgPool3×3(F_s)`

与 Normal Detail 使用：

- 相同特征来源；
- 相同注入位置；
- 相同 64→16 projection；
- 相同新增参数量 1040；
- 相同 zero-init endpoint。

---

#### 模型代码

`model/vitcross_seg_modeling_shallow_detail.py`

---

#### 训练代码

`scripts/train_vaihingen_P2H_Rare30_HFDetail_screen.py`

---

#### 公共预训练权重

`/home/jovyan/zzx/paper_rebuild/08_assets/pretrained/ftransunet/R50+ViT-B_16.npz`

---

#### 运行目录

`runs/Thesis_Ch4_NoSR_ScreenV4_Rare30_P2H_HFDetail_Vaihingen_P2H_seed42_formal160k`

---

#### 最终 checkpoint

`runs/Thesis_Ch4_NoSR_ScreenV4_Rare30_P2H_HFDetail_Vaihingen_P2H_seed42_formal160k/checkpoints/model_iter_010000.pth`

恢复状态：

`runs/Thesis_Ch4_NoSR_ScreenV4_Rare30_P2H_HFDetail_Vaihingen_P2H_seed42_formal160k/last_train_state.pth`

---

#### 结果文件

`runs/Thesis_Ch4_NoSR_ScreenV4_Rare30_P2H_HFDetail_Vaihingen_P2H_seed42_formal160k/best_registry.json`

`runs/Thesis_Ch4_NoSR_ScreenV4_Rare30_P2H_HFDetail_Vaihingen_P2H_seed42_formal160k/metrics_history.csv`

`runs/Thesis_Ch4_NoSR_ScreenV4_Rare30_P2H_HFDetail_Vaihingen_P2H_seed42_formal160k/p2h_diagnostics.csv`

---

#### 训练曲线

| Step | NB OA | NB mF1_fg5 | NB mIoU_fg5 |
|---:|---:|---:|---:|
| 2k | 91.3268 | 87.9698 | 79.2304 |
| 4k | 91.9192 | 89.2772 | 81.1579 |
| 6k | 91.9454 | 89.4842 | 81.4683 |
| 8k | 92.0275 | 89.9257 | 82.1490 |
| 10k | 92.2059 | 90.1041 | **82.4446** |

早期 2k 相比主基线同 step：

**+0.1786 mIoU**

10k：

**82.4446 vs 83.0658**

最终：

**-0.6212 mIoU**

---

#### 10k NB 各类结果

| 类别 | F1 | IoU | 相对主基线 IoU |
|---|---:|---:|---:|
| Impervious | 93.2936 | 87.4302 | -0.3425 |
| Building | 97.4620 | 95.0496 | -0.1206 |
| LowVegetation | 81.5141 | 68.7965 | +0.0229 |
| Tree | 91.5933 | 84.4904 | -0.0152 |
| Car | 86.6574 | 76.4562 | **-2.6506** |
| Clutter | 80.4643 | **67.3141** | **+67.3141** |

---

#### FullGT 10k

OA = 89.1334

mF1_fg5 = 86.4122

mIoU_fg5 = 76.6804

主基线 FullGT mIoU_fg5：

76.9410

下降：

**-0.2606**

---

#### 关键分析

HF Detail 与 Normal Detail 在最终 fg5 指标上几乎完全相同：

Normal：

82.4473

HF：

82.4446

两者仅差：

**0.0027 mIoU**

HF Detail 对 LowVegetation 和 Tree 基本无损：

LowVegetation：

+0.0229 IoU

Tree：

-0.0152 IoU

但 Car 显著下降：

**-2.6506 IoU**

与此同时 Clutter 从主基线的 0.0000 提升到：

**67.3141 IoU**

因此 HF Detail 并非完全无效，
而是显著改变了类别判别分配。

现有 per-class 指标不能证明 Car 是否直接被误分为 Clutter，
若需要确定具体错误流向，必须进一步分析 confusion matrix。

---

#### 结论

尽管 HF Detail 对 Clutter 的识别产生了非常大的变化，
但论文主要使用的 fg5 指标下降，
尤其 Car 小目标性能显著下降。

因此：

**HF Shallow Detail 不进入最终主方法。**

该实验仅作为分析证据保留，
用于说明简单浅层高频强化可能导致类别性能重新分配。

不继续进行 20k / 40k 扩展实验。

## 5. 已明确停止或淘汰的路线

### Decoder 端继续叠加频率模块

Vaihingen 与 Potsdam 均只有有限增益。

不再作为主要研究方向。

### Crop 256

2k NB mIoU 从 78.0476 降至 73.1822。

后续保持 crop 512。

### History30

整体弱于 Rare30，并明显伤害 Car。

停止比例搜索。

### Rare15 + History15

没有超过 Rare30，没有证明明显互补性。

停止。

### 完整浅层细节保持

10k NB mIoU_fg5：

82.4473

主基线：

83.0658

下降：

-0.6185。

五个前景类别全部下降。

停止。

### 高频浅层细节保持

10k NB mIoU_fg5：

82.4446

主基线：

83.0658

下降：

-0.6212。

LowVegetation / Tree 基本保持，
但 Car 下降 2.6506 IoU。

Clutter IoU 提升到 67.3141，
说明该结构明显改变了类别判别分配，
但没有提高主要 fg5 性能。

停止作为主线。

## 6. 后续实验计划

### 当前保留主线

当前统一 10k 最佳方案：

**Optical/DSM 跨模态高频可靠性 + Rare30**

NB：

- OA = 92.2850
- mF1_fg5 = 90.4897
- mIoU_fg5 = 83.0658

### 下一研究重点

后续结构修改优先围绕当前仍然较困难的类别展开：

- Car 小目标；
- LowVegetation / Tree 类别混淆与边界；
- 模态可靠性的进一步类别感知建模。

不再继续简单的浅层残差或浅层高频残差叠加。

任何新实验继续采用当前主基线作为统一 10k 对照。

### 暂不执行

- 不继续 Normal Detail 20k / 40k；
- 不继续 HF Detail 20k / 40k；
- 不继续 History 比例搜索；
- 不重新测试 crop 256；
- 不在当前没有明确假设的情况下继续堆叠 decoder 频率模块。

## 7. 历史名称与现在的人类可读名称

| 旧名称 | 现在统一理解 |
|---|---|
| F0 / DetPair F0 | 确定性 NoSR 双模态基础对照 |
| F1 | Decoder + LFAU |
| F2 | Decoder + LFAU + SGOR |
| F3 | Decoder + LFAU + SGOR + HFDC |
| P1 | 融合前 DSM 高频校准 |
| P2H | Optical/DSM 跨模态高频可靠性 |
| P1 + Rare30 | DSM 高频校准 + Rare30 |
| P2H + Rare30 | 跨模态高频可靠性 + Rare30 |
| P1 + C256 | DSM 高频校准 + Crop256 |
| History30 | 历史难例采样 30% |
| Rare15History15 | Rare15 + History15 |
| NormalDetail | 完整浅层细节保持 |
| HFDetail | 高频浅层细节保持 |
| ScreenV2 / V3 / V4 | 旧运行目录版本号，仅用于定位文件 |

---

## 8. 实验记录规则

以后新增正式实验之前，必须先在本文件建立对应小节。

每个实验至少写清楚：

**研究目的 → 对照实验 → 唯一变化 → 数据 → 模型代码 → 训练脚本 → 预训练权重 → checkpoint → run 目录 → 日志 → 结果 → 结论 → 下一步。**

实时训练输出继续保存在：

`runs/`

`runs/` 不进入 Git。

重要实验完成后，将关键轻量结果复制到：

`records/experiments/`

GitHub 不保存大型 checkpoint，只在本文件记录服务器真实路径。

---

最后更新：

2026-09-11

<!-- POTSDAM_CROSSDATASET_20260913_START -->

## Potsdam 跨数据集受控验证与可靠性审计（2026-09-12～2026-09-13）

实验代码基线 commit：`5b31dd2224248ffc5ff17af9e1d40f4159b95095`。

本轮固定使用 Potsdam Train18/Test6，crop=512，physical batch=4，gradient accumulation=4，effective batch=16，seed=42，统一训练 10,000 optimizer steps，每 2,000 step 评估一次。三组正式实验依次为“双模态 NoSR 基线”、“Optical/DSM 跨模态高频可靠性”和“Optical/DSM 跨模态高频可靠性 + Rare30”。

### 最终 10k 结果

| 方法 | Full OA | Full mF1_fg5 | Full mIoU_fg5 | NB OA | NB mF1_fg5 | NB mIoU_fg5 |
|---|---:|---:|---:|---:|---:|---:|
| 双模态 NoSR 基线 | 88.8687 | 89.2582 | 80.9084 | 91.1537 | 92.2380 | 85.9045 |
| 跨模态 HF Reliability | 88.6984 | 88.7866 | 80.1594 | 90.9838 | 91.8469 | 85.2439 |
| 跨模态 HF Reliability + Rare30 | **88.9744** | **89.3903** | **81.1305** | **91.2682** | **92.3091** | **86.0306** |

固定 10k 预算下，HF Reliability 单独相对基线的 NB mIoU_fg5 为 **-0.6606**；加入 Rare30 后相对 HF Reliability 为 **+0.7867**，相对基线最终为 **+0.1261**。FullGT mIoU_fg5 相对基线为 **+0.2221**。

### NB mIoU_fg5 训练曲线

| Iter | Baseline | HF Reliability | HF Reliability + Rare30 |
|---:|---:|---:|---:|
| 2k | 79.0694 | 78.8443 | 77.2369 |
| 4k | 83.0949 | 82.2920 | 83.2339 |
| 6k | 83.3900 | 83.2643 | **85.4545** |
| 8k | 83.7685 | 84.1692 | **85.1542** |
| 10k | 85.9045 | 85.2439 | **86.0306** |

Rare30 前期较慢，但在 6k～8k 阶段形成明显优势；到 10k 时基线继续追赶，因此最终增益较小。

### NB 逐类别 IoU

| 类别 | Baseline | HF Reliability | HF+Rare30 | HF−Base | Rare30−Base | Rare30−HF |
|---|---:|---:|---:|---:|---:|---:|
| Impervious | 87.1767 | 86.7740 | 87.4173 | -0.4027 | +0.2406 | +0.6433 |
| Building | 95.2536 | 95.0095 | 95.4745 | -0.2441 | +0.2209 | +0.4650 |
| LowVegetation | 77.4611 | 77.2918 | 77.4208 | -0.1692 | -0.0403 | +0.1289 |
| Tree | 76.9201 | 75.5345 | 77.0794 | **-1.3856** | +0.1593 | **+1.5449** |
| Car | 92.7112 | 91.6096 | 92.7609 | **-1.1015** | +0.0498 | **+1.1513** |
| Clutter | 45.6513 | 47.9302 | 49.8009 | +2.2789 | +4.1496 | +1.8707 |

HF Reliability 在 Potsdam 上主要损失出现在 Tree 和 Car；Rare30 能明显恢复这两个类别，但相对于原始 Baseline 的最终绝对增益很小。因此不应表述为“Rare30 显著提高 Potsdam 三个稀有类”，更准确的是“Rare30 显著修复 HF Reliability 下 Tree/Car 的退化”。

### 逐类别 HF reliability 审计

HF Reliability @10k 的 NB 平均 `(wo, wd)`：

| 类别 | Optical wo | DSM wd | Opt005 | DSM005 | Gap |
|---|---:|---:|---:|---:|---:|
| Impervious | 0.5468 | 0.4532 | 97.68% | 1.79% | 0.0974 |
| Building | 0.5402 | 0.4598 | 92.09% | 6.24% | 0.0926 |
| LowVegetation | 0.5479 | 0.4521 | 98.86% | 0.79% | 0.0972 |
| Tree | 0.5467 | 0.4533 | 98.03% | 1.39% | 0.0957 |
| Car | 0.5131 | 0.4869 | 71.74% | 24.90% | 0.0984 |
| Clutter | 0.5403 | 0.4597 | 92.42% | 6.01% | 0.0921 |

HF Reliability + Rare30 @10k 的 NB 平均 `(wo, wd)`：

| 类别 | Optical wo | DSM wd | Opt005 | DSM005 | Gap |
|---|---:|---:|---:|---:|---:|
| Impervious | 0.5535 | 0.4465 | 96.31% | 2.82% | 0.1127 |
| Building | 0.5428 | 0.4572 | 87.92% | 9.92% | 0.1068 |
| LowVegetation | 0.5539 | 0.4461 | 97.53% | 1.70% | 0.1105 |
| Tree | 0.5525 | 0.4475 | 96.09% | 2.75% | 0.1095 |
| Car | 0.5083 | 0.4917 | 66.58% | 29.98% | 0.1156 |
| Clutter | 0.5427 | 0.4573 | 88.52% | 9.28% | 0.1050 |

诊断结论：Rare30 并不是简单把 reliability gate 拉回 0.5。Tree 的 Optical 偏好反而增强，但 IoU 同时恢复；Car 则轻微向 DSM/更均衡方向移动。因此 Rare30 的收益不能简单归因于“修正错误的模态权重”，更可能来自 sampling 对 reliability gate 与后续特征/分类器联合学习的影响。

跨数据集诊断中，Vaihingen 既有结果显示 Tree 约为 `0.4992/0.5008`、Car 约为 `0.4752/0.5248`，而 Potsdam HF Reliability @10k 为 Tree `0.5467/0.4533`、Car `0.5131/0.4869`，显示明显的数据集/类别依赖。但 Vaihingen 该审计来自 20k checkpoint，而 Potsdam 来自 10k，因此目前作为机制诊断证据使用，不作为严格受控的跨数据集因果结论。

### 保存位置

机器可读汇总：`records/potsdam_crossdataset_3x10k_20260913/`

HF Reliability 完整审计：`records/potsdam_crossmodal_hf_reliability_10k_by_class_20260913/`

HF Reliability + Rare30 完整审计：`records/potsdam_crossmodal_hf_reliability_rare30_10k_by_class_20260913/`

三个正式 checkpoint 保留在对应 `runs/` 目录中；完整训练日志与 audit 日志保留在 `.local_backups/`，不提交 Git。

当前阶段结论：Potsdam 跨数据集验证已经完成。下一阶段可以研究语义/类别条件的跨模态可靠性，但在本轮记录与 Git 同步完成前不启动新实验。

<!-- POTSDAM_CROSSDATASET_20260913_END -->
## E50 Reliability-v2：HF quality cue diagnosis and hybrid reliability

日期：2026-09-13。

### E50-A：modality corruption gate smoke

基于 Potsdam Test6、固定 294 个 512×512 sparse windows，对已有
HF Reliability 与 HF Reliability + Rare30 的 10k checkpoint 做无训练诊断。

主要发现：

- DSM zero 时 gate 能弱幅度提高 Optical 权重：
  - HF：Δwo = +0.00184
  - HF+Rare30：Δwo = +0.00271
- DSM blur/down2 的响应非常弱，Δwo 约为 1e-4 量级。
- Optical blur/down2 时响应方向错误：
  - HF optical_blur5：Δwo = +0.00241
  - HF optical_down2：Δwo = +0.00167
  - HF+Rare30 optical_blur5：Δwo = +0.00456
  - HF+Rare30 optical_down2：Δwo = +0.00324

因此原 gate 不能直接解释为稳定的 modality-quality reliability estimator。

### E50-A2：raw HF / HF-retention audit

在 hfrely0 输入前的 S0 Optical/DSM 特征上直接检查 HF 信号。

HF checkpoint：

- Optical blur5：
  - RawO = -50.15%
  - RatioO = -52.27%
- Optical down2：
  - RawO = -43.13%
  - RatioO = -44.85%
- DSM blur5：
  - RawD = -8.84%
  - RatioD = -9.02%
- DSM down2：
  - RawD = -7.56%
  - RatioD = -7.69%
- DSM zero：
  - RawD = -48.43%
  - RatioD = +12.03%

HF+Rare30 给出相同趋势。

结论：

1. S0 特征内存在明显的 modality-quality HF 信号；
2. 原模型的 per-modality spatial HF normalization 会弱化绝对质量变化；
3. HF/feature ratio 也不能单独作为 reliability cue，因为 DSM zero 时比例可能反向增加；
4. 下一版应保留原 spatial HF cue，并加入跨模态共享归一化的 raw-HF quality cue。

### Reliability-v2 结构

新文件：

- `model/vitcross_seg_modeling_hf_reliability_v2.py`
- `scripts/train_potsdam_hf_reliability_v2_10k.py`

Hybrid cue 共 6 channels：

原 spatial cue：

- normalized Optical HF energy
- normalized DSM HF energy
- absolute spatial HF discrepancy

新增 shared raw-HF quality cue：

- qo = mean(Eo_raw) / (mean(Eo_raw) + mean(Ed_raw) + eps)
- qd = mean(Ed_raw) / (mean(Eo_raw) + mean(Ed_raw) + eps)
- |qo - qd|

context 参数量由 738 增至 1170。

最终 reliability logits 层继续 zero-init，因此初始化严格保持：

- wo = wd = 0.5
- So = Sd = 1
- calibrated Optical == original Optical
- calibrated DSM == original DSM

### Reliability-v2 training degradation

保持 Potsdam 原冻结协议：

- crop = 512
- physical batch = 4
- gradient accumulation = 4
- effective batch = 16
- seed = 42
- optimizer / LR / warmup / random-scale / flip 规则不变

仅加入独立 RNG 控制的模态质量增强：

- 70% clean
- 15% Optical degradation
- 15% DSM degradation

退化类型在被选择模态内 50/50：

- blur5
- downsample×2 -> resize

不加入 Rare30，不加入 shift。

### Static / identity gate

通过：

- parameter count = 1170
- context input channels = 6
- final reliability conv weight/bias = 0
- Optical identity max error = 0
- DSM identity max error = 0
- wo/wd initialization error from 0.5 = 0

### Deterministic smoke 20 × 2

两次独立进程：

- Rep A：20 optimizer steps
- Rep B：20 optimizer steps

结果：

- 20/20 loss 完全一致
- 20/20 mean50 完全一致
- LR 完全一致
- max |loss_A-loss_B| = 0
- max |mean50_A-mean50_B| = 0
- max |lr_A-lr_B| = 0

step 1：
- loss = 1.83890909
- wo/wd = 0.5 / 0.5

step 20：
- loss = 1.71921754
- mean50 = 1.79131564
- wo = 0.50021684
- wd = 0.49978316
- reliability gap = 0.00043895

判定：

`RELIABILITY-V2 DETERMINISTIC SMOKE: EXACT PASS`

### 下一阶段 gate

先正式训练到 2000 optimizer steps，而不是直接跑完 10k。

2000-step 后检查：

1. clean NB segmentation；
2. DSM blur/down2 是否满足 Δwo > 0；
3. Optical blur/down2 是否满足 Δwo < 0；
4. Tree / Car 是否存在明显异常。

机制方向通过后，再 resume 至 10000 steps。
