# 遥感双模态语义分割实验总时间线（截至 2026-10-09 完成作业快照21:43）

> 目的：把当前仓库内已经运行、已经停止、仅规划、技术失败和正在运行的实验统一整理成一份人类可读时间线。
>
> 当前工作分支：`rebuild-v1-protocol-20260915`。
>
> 当前共享入口仍以 `docs/START_HERE.md -> docs/current/RESEARCH_DECISION.md -> docs/current/PROJECT_STATUS.md -> docs/current/NEXT_EXPERIMENT.md` 为最高优先级；本文件负责历史实验梳理，不替代带时间观测状态。
>
> 重要说明：不同阶段的数据划分、训练预算、选模方式和综合指标定义并不完全相同，因此本文只在同一冻结协议内比较数值，不跨协议硬排“谁最好”。

---

## 1. 总体研究演化

项目研究主线大致经历了五个阶段：

1. **频率模块放在哪里最有效**：从 decoder 后端频率增强，转向融合前频率建模。
2. **频率是否能用于模态可靠性**：从 DSM-only 高频校准升级到 Optical/DSM 高频可靠性，并加入 Rare30。
3. **跨数据集与 GSD/物理尺度机制分析**：发现 Optical 与 DSM 的频率行为不同，DSM 更适合 physical-frequency 表示。
4. **REBUILD_V1 重新建立严格基线**：先证明 clean 双模态增益、退化后 harmful fusion、普通 corruption/dropout 基线，再研究选择性融合和缺失回退。
5. **当前主线**：RGB–DSM 条件互补、模态退化/缺失分割、参数隔离和局部条件支持。当前不再把“HF Reliability”或“Physical DSM”直接视为最终主方法。

---

# 2. 2026-08-28 ～ 2026-09-15：频率与可靠性探索阶段

## 2.1 2026-08-28｜Decoder 频率消融 F0–F3

**目的**：验证频率模块放在 decoder 后端是否能稳定提升分割性能。

**设计**：F0 普通上采样；F1=LFAU；F2=LFAU+SGOR；F3=LFAU+SGOR+HFDC。

**主要结果**：Vaihingen、Potsdam 均有小幅增益；Potsdam F0→F3 约 +0.2674 mIoU，Vaihingen 更小。

**结论**：频率后置有效但增益有限，不再继续在 decoder 堆频率模块。

**状态**：`COMPLETED / MAIN LINE STOPPED`。

## 2.2 2026-08-29 ～ 2026-08-31｜融合前 DSM 高频校准（旧名 P1）

**目的**：验证频率是否应该在 Optical/DSM 融合前使用。

**主要结果**：2k NB mIoU_fg5=78.0476，较同 step F0 77.4944 提升 +0.5532pp；40k 范围最佳 83.1941@34k，较 F0 最佳 82.7268 提升 +0.4673pp。

**结论**：融合前频率校准比继续叠加 decoder 频率更值得研究。

**状态**：`COMPLETED / EFFECTIVE`。

## 2.3 2026-08-31 ～ 2026-09-01｜Optical/DSM 跨模态 HF Reliability（旧名 P2H）

**目的**：由 DSM-only 高频校准升级为 Optical/DSM 高频差异驱动的空间模态权重。

**主要结果（Vaihingen）**：2k=78.6107；20k=83.1850 NB mIoU_fg5；Car 的平均权重更偏 DSM，高频权重表现出类别差异。

**当时结论**：在 Vaihingen 有阶段性有效性。

**后续修正**：9 月 13 日以后跨数据集与 corruption 审计证明，该 gate 不能稳定解释成真正的“模态质量可靠性估计器”。

**状态**：`HISTORICAL POSITIVE -> LATER DOWNGRADED`。

## 2.4 2026-09-01 ～ 2026-09-11｜Rare30、Crop256、History 与浅层细节

### Rare30

**目的**：增加 LowVegetation / Tree / Car 等困难和稀有类别在训练 crop 中的曝光。

**策略**：70% random + 30% rare；Rare 内 LowVeg/Tree/Car=0.25/0.25/0.50。

**结果**：P1+Rare30 10k=82.8807；HF Reliability+Rare30 10k NB OA=92.2850、mF1_fg5=90.4897、mIoU_fg5=83.0658。

**结论**：Rare30 有训练价值，作为采样策略保留。

### Crop256

**目的**：增加 patch 数和样本变化。

**结果**：2k NB mIoU 从 crop512 的 78.0476 降到 73.1822。

**结论**：需要更大上下文，后续保持 crop512。

### History30 / Rare15+History15

**目的**：测试长期分错区域是否比类别稀有性更值得重复采样。

**结果**：History30 10k=82.0895；Rare15+History15=82.2388，均低于 Rare30，并明显伤害 Car。

**结论**：停止 History 比例搜索。

### Normal / HF Shallow Detail

**目的**：在 HF Reliability+Rare30 后再次注入浅层结构/高频，改善边界和小目标。

**结果**：主基线 83.0658；Normal Detail 82.4473（−0.6185）；HF Detail 82.4446（−0.6212）。HF Detail 对 Clutter 大幅提高，但 Car IoU −2.6506。

**结论**：属于类别重分配而不是总体提升；两条路线停止。

## 2.5 2026-09-12 ～ 2026-09-13｜Potsdam 跨数据集受控验证

**目的**：验证 Vaihingen 上的 HF Reliability/Rare30 是否能跨到 Potsdam。

| 方法 | NB mIoU_fg5 |
|---|---:|
| 双模态 NoSR baseline | 85.9045 |
| HF Reliability | 85.2439 |
| HF Reliability + Rare30 | 86.0306 |

**关键现象**：HF 单独 −0.6606pp；Rare30 相对 HF +0.7867pp；最终相对 baseline 仅 +0.1261pp。HF 主要伤害 Tree/Car，Rare30 修复大部分退化。

**结论**：HF Reliability 不是稳定跨数据集增益模块；Rare30 更像训练分布修复；gate 行为存在数据集/类别依赖。

**状态**：`COMPLETED / ORIGINAL RELIABILITY CLAIM WEAKENED`。

## 2.6 2026-09-13｜E50 corruption audit 与 Reliability-v2

**E50-A 目的**：检验原 HF gate 是否真正感知模态质量。

**结果**：DSM zero 时 Optical 权重只略升；DSM blur/down2 响应极弱；Optical blur/down2 后 Optical 权重反而上升。

**结论**：原 gate 不能称为稳定的 modality-quality estimator。

**E50-A2**：S0 raw HF 中质量信号实际存在；Optical blur/down2 raw HF 下降约 50%/43%，DSM blur/down2 也有可见下降。

**结论**：问题主要在 cue/normalization 弱化绝对质量变化。

**Reliability-v2**：增加 shared raw-HF quality cue，工程/identity/deterministic smoke 通过，但未形成足够正式科学结果提升为主方法。

**状态**：`ENGINEERING PASS / NOT MAIN LINE`。

## 2.7 2026-09-13 ～ 2026-09-15｜Physical frequency / E51 Physical-DSM

**目的**：研究不同 GSD 下相同 pixel-frequency 的物理意义，以及 Optical/DSM 是否该共用同一频率坐标。

**机制审计**：Potsdam 5cm 模拟 6/7/8/9/10/12cm。DSM 在 physical-coordinate 下 profile 更稳定；Optical 不同，强制 physical normalization 可能变差。最稳定组合为 **PH=Pixel Optical + Physical DSM**。

**同预算分割结果**：

| GSD | PP4k | PH4k | PH增益 |
|---:|---:|---:|---:|
| 5cm | 82.3889 | 83.5771 | +1.1882 |
| 8cm | 78.3468 | 80.3240 | +1.9771 |
| 10cm | 75.0145 | 77.2999 | +2.2854 |
| 12cm | 71.9161 | 74.0833 | +2.1672 |

**重要负结果**：correct GSD / scale=1 / wrong GSD 的 test-time 结果几乎一致，因此不能声称推理阶段动态读取 GSD 带来收益。

**阶段结论**：DSM 更适合 physical-frequency training calibration；Optical 与 DSM 不宜盲目共用 physical coordinate；但跨 seed、跨数据集和长训练未确认。

---

# 3. 2026-09-16 ～ 2026-09-18：REBUILD_V1 严格基线重建

## 3.1 2026-09-16｜R01 true Optical-only

**目的**：建立真正单流 Optical-only 基线，完全无 DSM 分支。

**结果**：Val2 NB mIoU_fg5 最佳 85.3713@10k。

**结论**：成为 clean/退化条件下所有融合收益的匹配单模态参考。

## 3.2 2026-09-16｜R02 clean Optical+DSM + 16k budget freeze

**目的**：冻结统一 16k schedule，并建立 clean 双模态基线。

**结果**：NB mIoU_fg5 最佳 86.2016@13k；比 R01 +0.8303pp。

**结论**：clean 双模态系统优于真正 Optical-only，但全部增益不能直接归因 DSM。

## 3.3 2026-09-16 ～ 2026-09-17｜R03 / R04 / Core Matrix

**目的**：回答 clean DSM 是否有益、严重退化是否形成 harmful fusion、普通 corruption/dropout 能解决多少。

**结果**：R02 clean Fusion Gain +0.8303pp；DSM down8 变为 −0.4096pp；DSM zero −36.6016pp。R03 对轻中度退化强，但 missing DSM 失败；R04 大幅缓解 zero，但仍比 R01 fallback 低 2.2338pp。

**结论**：真正研究问题被明确为：保留 clean multimodal gain，同时坏 DSM 时逼近真实 Optical-only fallback。

## 3.4 2026-09-18｜C-OO capacity control

**目的**：区分 DSM 信息价值与双流容量价值。

**结果**：Optical+Optical NB 最佳约 86.3548，高于 R02 86.2016。

**结论**：R02−R01 的 clean 增益不能简单称为 DSM-specific gain；容量是重要混淆因素。

## 3.5 2026-09-18｜R05 Q+D 与 C-OO-QD

**目的**：联合 quality corruption + modality dropout，并使用匹配容量控制。

**结果**：R05 clean NB 约 87.0486；C-OO-QD 最佳约 86.1969。

**结论**：Q+D 下 DSM 双模态重新显示相对匹配容量控制的优势，但必须继续检查 missing/local/cross-seed 和 routing。

---

# 4. 2026-09-19 ～ 2026-09-23：局部退化、专家互补、蒸馏与收益预测

## 4.1 D1–D3｜local missing / shift / local down8

**目的**：把全局退化扩展到局部缺失、错位、局部分辨率降低，验证 harmful fusion 是否局部化。

**结论**：形成后续 damaged-region / boundary paired diagnostic 基础。

## 4.2 A1/A2、Seed17、D4–D6｜dropout、跨 seed、frozen expert routing

**目的**：检查 dropout、跨 seed 稳定性及 R01/R05 frozen experts 的互补和安全路由。

**结论**：safe max-confidence 在若干 family 有潜力，但不同规则并非完全公平同 fallback；frozen expert routing 只是潜在工程路线，还不是可训练单模型贡献。

## 4.3 2026-09-20 ～ 2026-09-22｜B1/B2/B3/B4：可靠性教师蒸馏

**目的**：区分继续训练、普通教师、可靠性教师、显式 fallback 约束和平均教师。

**seed42**：可靠性教师 KD 相对 CE continuation 在 clean/down8/zero 小幅正增益，相对普通 R05 teacher 在多项退化比较方向更优。

**seed17**：全局方向仍略有利，但局部 damaged 指标反转。

**结论**：seed42 观察不能升级为跨 seed 主结论；路线降级。

## 4.4 2026-09-22｜D7 data/scale/semantic-error audit

**目的**：定位失败来自数据尺度、类别语义还是结构融合。

**结论**：完成诊断，但没有足够强因果证据触发单独主线。

## 4.5 2026-09-22｜D8 sampling screen

**目的**：测试类别/区域/状态采样。

**结论**：固定 gate 未通过，不扩大搜索。

## 4.6 2026-09-23｜D9A / D9B DSM benefit prediction

**D9A**：confidence/entropy/disagreement 判断 DSM 是否有益。Entropy 有一定排名信息，但 safe entropy routing 4 wins / 10 losses / 2 ties。

**D9B**：在决策改变像素上利用 semantic/frequency/expert evidence；六分数 gate 失败。

**结论**：简单 benefit predictor 不能稳定支撑选择性 DSM。

## 4.7 2026-09-23｜D10M / D11

**D10M**：保持 amplitude 的空间扰动与 rescue，固定 gate 失败。

**D11**：监督 benefit/harm probe + off-Val2 calibration，gate 失败。

**结论**：没有建立稳定 benefit/harm predictor。

---

# 5. 2026-09-24 ～ 2026-09-28：更深结构、风险代理、FM/adapter 与独立数据

## 5.1 2026-09-24｜D12 deep decoder context/frequency/capacity

**目的**：检查上下文层级、频率表达或容量是否是瓶颈。

**结论**：gate 未通过；继续加深 decoder/context/frequency 不是当前突破口。

## 5.2 2026-09-25｜D13 RGB-anchored DSM residual + risk surrogate

**目的**：以 RGB 为锚，仅预测 DSM 有帮助时注入 DSM residual。

**结果**：Stage1 完成；两 seed gate 失败；Stage2 跳过。

**结论**：当前 residual/risk 实现不成立。

## 5.3 2026-09-26｜D14 DSM-content sensitivity

**目的**：固定 D13 head，只改变 DSM 内容，验证模型是否真正响应 DSM。

**结论**：存在 sensitivity，但“会响应 DSM”不等于“知道什么时候应该使用 DSM”。

## 5.4 2026-09-27｜D16 / D17

**目的**：intervention consistency、geometry auxiliary supervision及匹配控制。

**结果**：16/16 完成，A2/B1 gate 失败。

**结论**：没有建立稳定新增贡献。

## 5.5 2026-09-28｜D18 / D19 + seed17 replication

**目的**：frozen-DINO/pretrained adapter 与 intervention structures，做 seed42/17 匹配复验。

**结果**：P2 在两个 seed 相对同 seed P0/P1 有正增益；但 DSM 完全缺失时 P2 仍比 P0 低约 0.4–0.5pp。

**结论**：FM/adapter 有 clean 增益线索，但 missing-modality 安全问题仍未解决。

## 5.6 2026-09-28｜D20 independent-source audit

**目的**：寻找 GAMUS/US3D 等独立数据验证跨地域稳定性。

**结论**：来源/地理元数据与使用条件仍存在阻塞；不能把 Val2 双 seed 当成跨地域泛化。

---

# 6. 2026-09-29 ～ 2026-10-04：细粒度频率、适配、保护/恢复与路由机制排查

## 6.1 2026-09-29｜D21 detail-frequency controls

**目的**：严格匹配 fine-scale height 与 low/high frequency，对准确性与 missing-DSM safety 做两数据集两 seed 验证。

**状态**：32/32 完成。

**结论**：accuracy gate 和 missing safety gate 均失败；当前 detail-frequency 配方不升级主线。

## 6.2 2026-09-29 ～ 2026-10-01｜Post-D21 多方向组合

**目的**：系统测试 adaptation、conditional DSM residual、联合 LR、factorial interaction、mixed degradation，并做吞吐评估。

**状态**：主 42/42 完成，mixed 4/4 完成并审计。

**结论**：大量组合给出机制边界，但没有稳定取代强基线的新方法。

## 6.3 2026-10-01｜D23 frozen experts + semantic/frequency/utility gate

**目的**：冻结专家+语义/频率/效用 gate 是否能优于强融合。

**结果**：TSF 综合比 M0_safe 低 0.148998pp；减害同时丢失纠错。

**结论**：全部机制门槛未过；确定性 fallback 是工程能力而非研究贡献。

## 6.4 2026-10-02｜D24

**目的**：适配、增强、Pair 约束、语义/KD。

**结论**：部分解冻和普通增强是强基线；A1/A3 Pair loss 实际未启用，因此不能当作 Pair 科学负结果。

## 6.5 2026-10-02｜D25

**目的**：修正 Pair；测试状态分头与完整/缺失梯度投影。

**结论**：四项预设机制均未过；真实 Pair 已启用。当前采样梯度不支持“全局梯度冲突”作为主要解释。

## 6.6 2026-10-03｜D26

**目的**：双向特征交互、容量、语义/频率打乱。

**结果**：普通 B0 融合对 RGB 综合 +0.690973pp；XSF 对 B0 仅 +0.156829pp。

**结论**：普通融合本身是强基线；复杂双向交互没有达到增量和双侧保护门槛。

## 6.7 2026-10-03｜D27 原队列与修复队列

**原队列**：KeyError treatment 导致 step0 技术失败，**不能视为科学负结果**。

**修复后 10/10**：保护+恢复相对匹配对照损失约 1.77–1.89pp；保留更多 DSM 独有信息时伴随 RGB 原正确像素损失。

**结论**：当前 protection/recovery、dynamic expert、local/class routing 均未过门槛；揭示“保护原正确”与“保留另一模态纠错”存在明显取舍。

## 6.8 2026-10-03｜D28

**目的**：相同边际损伤下比较共同受损和独立受损。

**结果**：B0 独立−共同仅 +0.014570pp，未过 0.3pp。

**结论**：本轮不支持“共同受损”作为主要假设，原 D29 不触发。

## 6.9 2026-10-04｜D30

**目的**：拆解 protection/recovery loss，比较面积/像素归一化，并做固定 checkpoint 路由干预。

**结果**：P 对 S0 +0.041182pp；R −2.013409pp；PR_area −0.064718pp；PR_pixel −1.291674pp。

**结论**：四项继续门槛均 False；归一化可缓解损失但没有建立贡献。

## 6.10 2026-10-04 ～ 2026-10-05｜Post-D30 A/B/C/F

**A**：对齐范围/错配/权重；A2 对 A0 仅 +0.101643pp，低于 A1/A3，gate=False。

**B**：局部对应/增强；B3 gate=False。

**C**：缺失知识迁移/正确掩码 KL；固定候选 C2 双侧门槛 False。普通监督已经解释主要改善，不能把收益归因跨模态蒸馏。

**F**：条件频率干预因上游 gate 未过而实际 `SKIPPED_GATE`。

**结论**：不通过换名称、换小权重继续救同一失败配方。

---

# 7. 2026-10-05 ～ 2026-10-08：N1/N2/N5/N3/S1 条件互补阶段

## 7.1 2026-10-05｜N1 多深度入口与适配

**目的**：判断多深度/多投影尺度入口是否优于普通末端适配。

**关键结果**：N1-2（末端部分适应）S_available=86.239697；N1-3（多深度+部分适应）=85.358638。N1-3 对 N1-2 −0.881059pp，但相对冻结 N1-1 +2.789492pp。

**结论**：普通适应是强基线；多深度入口没有超过匹配适应对照，gate=False。

## 7.2 2026-10-05 ～ 2026-10-06｜N2 3×3关系传播 + E0/E1/E2

**N2 目的**：测试空间控制、DSM高度→RGB、RGB特征→DSM、双向固定候选及空间打乱。

**结果**：六组完成并独立验收；固定双向候选 gate=False；S 对空间控制 −0.007028pp，方向/打乱增量均未过。

**结论**：当前 3×3 relation 配方关闭，不扫窗口/预算/seed。

**E0/E1/E2 零训练诊断**：E1 显示 RGB 缺失且高 DSM 变化区域存在问题信号；E0 显示边界伤害率明显高于内部；E2 显示 RGB 错误缺失标记代价较大。这些是“问题存在”的诊断，不是方法有效证据。

## 7.3 2026-10-06｜N5 mixed-missing training

**目的**：根据 E1 的问题信号，测试混合缺失训练及位置相关处理是否优于普通适应。

**结果**：N5-3 相对随机 N5-1 仅 +0.041878pp；clean/DSM全缺失相对 N5-0 分别 −0.191071/−0.152271pp，超过保护底线。

**结论**：固定 N5-3 gate=False，当前 mixed-missing 配方关闭；普通适应仍是强控制。

## 7.4 2026-10-07｜E3/E4 与 N5 边界复查

**目的**：进一步拆解局部边界、feature/output、mask/context 问题。

**结果**：R1 问题门槛不通过；但 E4 在 C=0 条件下发现 RGB feature/context 问题信号，N1-2 RGB pooled 增量约 +1.307603pp，两个 tile 同方向；DSM 方向未过。

**结论**：支持继续测试“保留融合上下文是否有助于 RGB 缺失局部修复”，但不能称为双向贡献。

## 7.5 2026-10-07 ～ 2026-10-08｜N3 / S1 九组

**N3 目的**：测试条件区域归属是否能超过 local/grid 简单控制。

**N3 结果**：固定候选 N3-4 相对 local −0.000078pp，相对 grid +0.001937pp。

**N3 结论**：增量门槛失败，当前区域配方关闭。

**S1 目的**：把 feature-support 与 output correction 拆成四格，判断局部条件支持是否有真实价值。

**S1 关键结果**：S1-3 RGB 局部 U 相对 S1-0 **+4.102047pp**，两个 tile 均正；DSM −0.023201pp 且方向不稳；worst `aux_shift8/3_11` **−0.391546pp**，违反 −0.2pp 保护线。

**S1 结论**：发现很强的 RGB 单向局部恢复线索，但当前训练同时带来退化场景代价，所以旧 gate 仍 False，不能升级为最终方法。

---

# 8. 2026-10-08：当前 Post-S1 主实验

## 8.1 研究目的

解释 S1 的 +4.102pp 到底来自哪里，并尝试保留局部缺失收益，同时避免完整/退化场景被训练参数污染。

当前核心假设从“再设计一个 gate”转为：

1. **参数隔离**：修复 missing/local 状态时，是否应冻结主基座，避免破坏正常输入；
2. **保留上下文**：局部缺失区域是否仍需要来自原融合分支的上下文；
3. **局部修正**：仅修改需要修正的区域，避免整图策略变化。

## 8.2 D0 / D1 / P0–P9 / E

- **D0**：0训练，复用已有预测和双模型拼接，建立零训练、可观测mask路由的简单拼接对照；
- **D1**：同一权重下比较不同策略，区分 routing 问题与 parameter contamination；
- **P0–P9**：10组×8000新步，共80000 updates，比较共享/冻结基座、mask/context、全域/局部修正，并加入空间打乱与简单 calibration 机制控制；
- **P7**：事前指定候选“冻结基座 + 保留上下文 + 局部修正”，不是跑完后挑最好；
- **E**：6种压力条件、0训练，用于检查 clean/退化/缺失保护；
- **Q**：DSM 镜像方向仅条件储备，不自动运行。

## 8.3 截至 2026-10-08 23:53 的真实状态

- 当前工作提交：`8cb04ac456296b72d7c8302745c25f18b60c4ea2`；
- controller PID 1890742 `LIVE=True`；
- 阶段：`PREPARING_D0_MASKS`；
- CPU 已报告 `D0 / 3_11 / rgb_U`；
- D1、P0–P9、E 均尚未启动 GPU 科学作业；
- 0/10 新训练完成；
- GPU 空闲符合 CPU preparation 阶段，不能据此判为故障。

**当前结论**：Post-S1 尚无新科学结果，不能提前把 P7 或任何 P 组写成有效方法。

---

## 8.4 2026-10-09 21:25｜GPU0推进至P3

最后服务器只读查询（用户终端）：QUERY_OBSERVED=2026-10-09T21:25:10.899578+08:00；queue LAST_OBSERVED=21:25:10.879724，RUNNING_P3，controller PID1890742 LIVE=True，仅GPU0。CPU=COMPLETE、D1 COMPLETE（0更新，约43分01秒）；P6/P7/P8/P9/P4/P5/P2七组COMPLETE/8000，worker LIVE=False。P3 PID2437737 LIVE=True、8000/8000，checkpoint_selection阶段，正在3_11/dsm_missing的验证/评价；该标签继承旧进度命名，本轮主比较仍固定8000。P0/P1和E PENDING；Q=RESERVED_NOT_AUTOMATIC。没有本次故障回报，尚无科学分数/屏幕门槛/轻量原件验收，不能用loss或完成状态判有效。

截至21:25的条件估时：还需约10—14h，参照约2026-10-10 07:25—11:25（Asia/Shanghai），非保证。六冻结完整worker实测约1h56m—2h31m，P2共享更新完整worker3h57m53s；P3已训练完但完整评价剩余未测，另两共享组预计各约4h，E仍按1.5—4h规划及汇总开销估算。不是只用remaining_train_hours=0推断整队已完，也不含Q四组。

原科学协议/主候选保持，七P完整结束属于技术状态，当前没有本批精度与gate验收结论。继续P3→P0→P1→E，科学原件待收；不得把冻结/局部支持自动承诺为主线贡献。登记/执行仍为2c5e7d6，当前状态入口见docs/current。R0是零训练简单路由对照，GT oracle才是诊断上限。

---


## 8.6 Post-S1七完整作业阶段验收（2026-10-09）

原件77d3970f，快照21:43:00、queue21:42:23；D1/P6/P7/P8/P9/P4/P5/P2已收并分析，P3/P0/P1/E未齐。[完整阶段结果](POST_S1_PARTIAL_RESULTS_20261009.md)。P7 RGB_U对基线+2.562756pp，对匹配掩码控制+1.759726pp、空间打乱+1.952962pp、校准+2.207993pp，两tile正；冻结局部普通/全缺失/DSM_U保护为0变化。但R0已有双模型可观测mask拼接85.001650%，P7落后1.426292pp，违反事前−0.2pp底线。固定候选具体gate失败，不否定条件互补问题；Q固定DSM信号−0.050601pp/方向不一致也未过。

保留空间上下文与隔离保护的开发线索，后续补齐原队列共享八格与E边界；不后验换P3/P5、改门槛、追加seed/GPU1或训练Q。范围是反复开发Val2/seed42，无独立final/Test6。本轮状态入口已接收精度原件，8.5此前待收条目是带时间历史。

# 9. 当前已明确停止/降级的路线

- 继续堆 decoder frequency；
- Crop256；
- History30 / Rare15+History15；
- Normal/HF shallow detail；
- 原 HF gate 作为“稳定模态质量估计器”的解释；
- 简单 confidence/entropy/disagreement routing；
- 当前 benefit/harm predictor；
- 当前 RGB-anchored residual/risk surrogate；
- 当前 intervention/geometry auxiliary；
- D21 detail-frequency 配方；
- D23 semantic/frequency/utility gate；
- D25 Pair/gradient projection 配方；
- D26 XSF；
- D27 protection/recovery/router 具体配方；
- D28共同受损主假设；
- D30 loss拆解具体配方；
- Post-D30 A/B/C/F；
- N1多深度入口；
- N2 3×3 relation；
- N5 mixed-missing；
- N3 当前区域配方。

这些“停止”只针对已测试的具体实现，不等于否定整个研究问题。

---

# 10. 当前仍保留的可靠结论

1. Clean Optical+DSM 系统可以优于真正 Optical-only，但必须用容量控制避免把双流容量误算为 DSM 信息价值。
2. DSM 严重退化可以把正 fusion gain 变成负 fusion gain，harmful fusion 是真实开发集现象。
3. 普通 corruption training 和 modality dropout 是非常强的基线，新方法必须与其比较。
4. 模态缺失/退化下仍存在回退差距，说明条件互补问题尚未解决。
5. 多轮实验显示“保护原正确预测”和“保留另一模态独有纠错”存在明显取舍。
6. S1 暴露出很强的 RGB 局部条件支持收益，但同时存在参数污染/保护失败，因此当前最值得研究的是隔离更新与局部条件支持，而不是继续堆 gate。
7. 早期 physical-frequency 结果仍是有价值的机制证据，但目前不是最新主实验路线。

---

# 11. 新对话建议读取顺序

1. `docs/START_HERE.md`
2. `docs/current/RESEARCH_DECISION.md`
3. `docs/current/PROJECT_STATUS.md`
4. `docs/current/NEXT_EXPERIMENT.md`
5. 本文件 `docs/experiments/ALL_EXPERIMENTS_TIMELINE_20261008.md`
6. 需要具体数值时再打开对应 `docs/experiments/*RESULTS*.md` 和 `records/` 原件。

本时间线用于“理解整个研究为什么走到今天”；实时运行状态仍以 `docs/current/` 为准。
