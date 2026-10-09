# 遥感双模态语义分割实验总时间线（截至 2026-10-08）

> 目的：把当前仓库内已经运行、已经停止、仅规划、技术失败和正在运行的实验统一整理成一份人类可读时间线。
>
> 当前工作分支：`rebuild-v1-protocol-20260915`。
>
> 当前实时入口仍以 `docs/START_HERE.md -> docs/current/RESEARCH_DECISION.md -> docs/current/PROJECT_STATUS.md -> docs/current/NEXT_EXPERIMENT.md` 为最高优先级；本文件负责历史实验梳理，不替代实时状态。
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

**设计**：
- F0：普通上采样；
- F1：LFAU；
- F2：LFAU + SGOR；
- F3：LFAU + SGOR + HFDC。

**主要结果**：Vaihingen、Potsdam 都有小幅增益；Potsdam F0→F3 约 +0.2674 mIoU，Vaihingen 更小。

**结论**：频率后置有效但增益有限，不再继续在 decoder 堆频率模块。

**状态**：`COMPLETED / MAIN LINE STOPPED`。

---

## 2.2 2026-08-29 ～ 2026-08-31｜融合前 DSM 高频校准（旧名 P1）

**目的**：验证频率是否应该在 Optical/DSM 融合前使用，而不是只在 decoder 后端修补。

**主要结果**：
- 2k NB mIoU_fg5：78.0476，较同 step F0 77.4944 提升 +0.5532 pp；
- 40k 范围最佳：83.1941 @34k；
- 对照 F0 最佳：82.7268；
- 最佳增益约 +0.4673 pp。

**结论**：融合前频率校准比继续叠加 decoder 频率更值得研究。

**状态**：`COMPLETED / EFFECTIVE`。

---

## 2.3 2026-08-31 ～ 2026-09-01｜Optical/DSM 跨模态 HF Reliability（旧名 P2H）

**目的**：由 DSM-only 高频校准升级为 Optical/DSM 高频差异驱动的空间模态权重，尝试判断当前位置更应相信哪个模态。

**主要结果（Vaihingen）**：
- 2k NB mIoU_fg5：78.6107；
- 20k NB mIoU_fg5：83.1850；
- Car 的平均权重更偏 DSM，高频权重表现出类别差异。

**当时结论**：HF Reliability 在 Vaihingen 有阶段性有效性，进入快速组合筛选。

**后续修正**：9 月 13 日以后跨数据集和 corruption 审计证明，该 gate 不能稳定解释成真正的“模态质量可靠性估计器”。

**状态**：`HISTORICAL POSITIVE -> LATER DOWNGRADED`。

---

## 2.4 2026-09-01 ～ 2026-09-11｜Rare30、Crop256、History 与浅层细节

### Rare30

**目的**：增加 LowVegetation / Tree / Car 等困难和稀有类别在训练 crop 中的曝光。

**策略**：70% random crop + 30% rare crop；Rare 内 LowVeg/Tree/Car = 0.25/0.25/0.50。

**主要结果**：
- P1 + Rare30 10k：NB mIoU_fg5 = 82.8807；
- HF Reliability + Rare30 10k：NB OA 92.2850，mF1_fg5 90.4897，mIoU_fg5 = **83.0658**。

**结论**：Rare30 有训练价值，作为采样策略保留；不应与可靠性机制混为一谈。

### Crop256

**目的**：增加 patch 数和样本变化。

**结果**：2k mIoU 从 512 crop 的 78.0476 降到 73.1822。

**结论**：模型需要较大上下文，后续保持 crop512。

### History30 / Rare15+History15

**目的**：测试“历史长期分错区域”是否比类别稀有性更适合作为采样依据。

**结果**：History30 10k = 82.0895；Rare15+History15 10k = 82.2388，均低于 Rare30；Car 受损明显。

**结论**：停止 History 比例搜索。

### Normal / HF Shallow Detail

**目的**：在 HF Reliability + Rare30 基础上，再注入浅层结构或浅层高频是否改善边界/小目标。

**结果**：
- 主基线：83.0658；
- + Normal Detail：82.4473（−0.6185）；
- + HF Detail：82.4446（−0.6212）。

HF Detail 对 Clutter 有极大提升，但 Car IoU −2.6506，属于明显类别重分配而非整体提升。

**结论**：两条浅层细节路线均停止，不做 20k/40k 扩展。

---

## 2.5 2026-09-12 ～ 2026-09-13｜Potsdam 跨数据集受控验证

**目的**：验证在 Vaihingen 上阶段性有效的 HF Reliability / Rare30 是否能在 Potsdam 保持收益。

**统一 10k 结果（Potsdam）**：

| 方法 | NB mIoU_fg5 |
|---|---:|
| 双模态 NoSR baseline | 85.9045 |
| HF Reliability | 85.2439 |
| HF Reliability + Rare30 | 86.0306 |

**关键现象**：
- HF Reliability 单独相对 baseline：−0.6606 pp；
- 加 Rare30 后相对 HF：+0.7867 pp；
- 最终相对 baseline：仅 +0.1261 pp；
- HF Reliability 主要伤害 Tree / Car，Rare30 能修复大部分退化。

**结论**：
1. HF Reliability 不是稳定跨数据集增益模块；
2. Rare30 的主要作用更像训练分布修复；
3. gate 行为具有数据集和类别依赖性。

**状态**：`COMPLETED / ORIGINAL RELIABILITY CLAIM WEAKENED`。

---

## 2.6 2026-09-13｜E50 corruption audit 与 Reliability-v2

### E50-A：已有 checkpoint 的模态退化 gate audit

**目的**：检验原 HF gate 是否真的感知 Optical/DSM 质量。

**结果**：
- DSM zero 时 Optical 权重只小幅上升；
- DSM blur/down2 响应非常弱；
- Optical blur/down2 后，Optical 权重反而上升，方向错误。

**结论**：原 HF gate 不能直接称为稳定的 modality-quality reliability estimator。

### E50-A2：raw HF / HF-retention

**目的**：判断问题在于前端没有 quality signal，还是 gate cue 把 signal 弱化。

**结果**：Optical blur/down2 可使 raw HF 下降约 50%/43%；DSM blur/down2 也有可见下降。

**结论**：质量信号本身存在，但 per-modality spatial normalization 会弱化绝对质量变化。

### Reliability-v2

**设计**：在原 spatial HF cue 上增加跨模态 shared raw-HF quality cue，6-channel context，70% clean + 15% Optical degradation + 15% DSM degradation。

**结论**：工程/identity/deterministic smoke 通过，但当时没有形成足够正式结果把它提升为主方法。

**状态**：`ENGINEERING PASS / NOT MAIN LINE`。

---

## 2.7 2026-09-13 ～ 2026-09-15｜Physical frequency / E51 Physical-DSM

**目的**：研究同一 pixel-frequency 在不同 GSD 下是否代表不同物理尺度，以及 Optical 与 DSM 是否应该采用相同频率坐标。

### 机制审计

Potsdam 5cm 模拟 6/7/8/9/10/12cm GSD。

**主要发现**：
- DSM 在 physical-coordinate 下的频率 profile 更稳定；
- Optical 不表现出相同行为，强制 physical normalization 可能变差；
- 最稳定组合是 **PH = Pixel Optical + Physical DSM**。

例如 synthetic GSD 下 PH 相对 PP 的 profile drift reduction 多数约 23%–46%，而 HP（Physical Optical + Pixel DSM）显著变差。

### E51-B：真正分割模型 PH vs PP

严格同训练步数 4k：

| GSD | PP4k | PH4k | PH 增益 |
|---:|---:|---:|---:|
| 5 cm | 82.3889 | 83.5771 | +1.1882 |
| 8 cm | 78.3468 | 80.3240 | +1.9771 |
| 10 cm | 75.0145 | 77.2999 | +2.2854 |
| 12 cm | 71.9161 | 74.0833 | +2.1672 |

**重要负结果**：正确 test-time GSD、强制 scale=1、故意错误 GSD 的预测几乎一致，不能声称“推理时动态 GSD 注入”导致收益。

**阶段结论**：
- DSM 更适合 physical-frequency training calibration；
- Optical 与 DSM 不应盲目共用同一 physical-frequency coordinate；
- same-step PH 提高 native accuracy 和 synthetic-GSD robustness；
- 但更长训练、跨 seed、跨数据集还未确认。

**后续角色**：这是重要机制证据，但 9 月 16 日以后项目转入更严格的 REBUILD_V1 模态互补/退化主线，PH 没有被直接认定为最终方法。

---

# 3. 2026-09-16 ～ 2026-09-18：REBUILD_V1 严格基线重建

## 3.1 2026-09-16｜R01 true Optical-only

**目的**：建立真正单流 Optical-only 基线，不允许 DSM 分支存在，用来衡量真正的 fusion gain。

**结果**：Val2 NB mIoU_fg5 最佳 85.3713 @10k。

**结论**：成为 clean/退化情况下所有融合收益的匹配单模态参考。

---

## 3.2 2026-09-16｜R02 clean Optical+DSM + 16k budget freeze

**目的**：冻结统一 16k 完整 schedule，并建立 clean 双模态 F0 基线。

**结果**：Val2 NB mIoU_fg5 最佳 86.2016 @13k；比 R01 +0.8303 pp NB。

**结论**：clean 双模态系统确实优于真正 Optical-only，但当时还不能把全部增益归因 DSM，因为双流还多了容量和交互计算。

---

## 3.3 2026-09-16 ～ 2026-09-17｜R03 / R04 / Core Matrix

**研究问题**：
1. clean DSM 是否有正融合收益；
2. DSM 变坏后是否会转成 harmful fusion；
3. 普通 corruption training 能解决多少；
4. 普通 modality dropout 能解决多少。

**核心结果**：
- R02 clean Fusion Gain：+0.8303 pp NB；
- R02 DSM down8：Fusion Gain = −0.4096 pp；
- R02 DSM zero：−36.6016 pp，灾难性失效；
- R03 corruption training 对轻中度退化很强，但 DSM zero 仍失败；
- R04 modality dropout 大幅修复 DSM zero，但仍比 R01 fallback 低 2.2338 pp。

**结论**：
- “clean 模态有益、严重退化后融合反而有害”得到直接证据；
- corruption/dropout 是必须击败的强基线；
- 真正值得研究的问题变成：保留 clean multimodal gain，同时在坏 DSM 时逼近真实 Optical-only fallback。

---

## 3.4 2026-09-18｜C-OO capacity control

**目的**：区分“DSM 信息价值”与“仅仅多一个分支/更多容量”。

**结果**：C-OO（Optical+Optical）NB 最佳约 86.3548，高于 R02 的 86.2016。

**结论**：R02 相对 R01 的 clean 增益不能简单称为 DSM-specific gain；双流容量本身就是强解释变量。

---

## 3.5 2026-09-18｜R05 Q+D 与 C-OO-QD

**目的**：联合 quality corruption + modality dropout，并使用匹配 Optical+Optical Q+D 控制，进一步隔离 DSM 特异信息。

**主要结果**：R05 clean NB mIoU_fg5 约 87.0486；C-OO-QD 最佳约 86.1969。

**结论**：在更强 Q+D 训练下，DSM 双模态再次表现出相对匹配容量控制的优势，但仍必须继续检查缺失、局部退化、跨 seed 和路由机制；不能仅凭 clean 总分建立最终贡献。

---

# 4. 2026-09-19 ～ 2026-09-23：局部退化、专家互补、蒸馏与收益预测

## 4.1 D1–D3｜局部 missing / shift / local down8

**目的**：把全局 corruption 扩展到局部缺失、错位和局部分辨率退化，验证 harmful fusion 是否具有空间局部性。

**结论**：完成了局部退化基准，成为后续 damaged region / boundary paired diagnostic 的基础；早期记录部分主要来自用户回报，证据等级低于后续完整原件审计。

---

## 4.2 A1/A2、Seed17、D4–D6｜dropout、跨 seed 与 frozen-expert routing

**目的**：
- 检查训练 dropout 的贡献；
- seed17 复核 R01/R05/C-OO-QD；
- 使用 R01/R05 frozen experts 测试专家互补与安全路由。

**关键发现**：
- R05 在 seed42/17 的局部退化表现并不完全一致；
- safe max-confidence 在若干 missing/degraded family 上能改善，但不同路由规则没有完全公平的同一 fallback 条件；
- frozen expert 路由显示“选择哪个专家”有潜力，但还不是可直接落地的单网络方法。

**结论**：转向训练阶段可靠性教师与更严格的 paired diagnostic。

---

## 4.3 2026-09-20 ～ 2026-09-22｜B1/B2/B3/B4：可靠性教师蒸馏

**目的**：区分继续训练、普通双模态教师、可靠性教师、显式 fallback 约束和平均教师的贡献。

**seed42 结果**：可靠性教师 KD 相对 CE continuation 在 clean/down8/zero 均有小幅正增益；相对普通 R05 teacher，在 DSM 退化和八项局部 paired comparison 中方向更优。

**B4 seed17**：全局 down8/zero 方向仍略有利，但局部 damaged 指标相对 R05_KD 反转。

**结论**：seed42 的“可靠性教师”观察不能升级为跨 seed 主结论；该路线降级，不作为最终论文主机制。

---

## 4.4 2026-09-22｜D7 数据/尺度/语义错误审计

**目的**：判断现有失败更接近数据尺度、类别语义还是结构性融合问题。

**结论**：完成诊断，但没有给出足以单独触发新主线的强因果证据；后续进入采样与收益判断实验。

---

## 4.5 2026-09-22｜D8 C/A/S sampling screen

**目的**：测试类别/区域/状态相关采样是否能修复弱侧和困难样本问题。

**结论**：固定 gate 未通过；没有证据支持继续沿当前采样实现扩大搜索。

---

## 4.6 2026-09-23｜D9A / D9B：DSM benefit prediction

### D9A

**目的**：直接用 confidence / entropy / expert disagreement 判断“当前像素使用 DSM 是否有益”。

**结果**：entropy ranking 有一定正向信息；disagreement interaction 方向不理想。安全 entropy route 实际比较为 4 wins / 10 losses / 2 ties。

**结论**：简单 confidence/entropy/disagreement 不能稳定完成 benefit routing。

### D9B

**目的**：在真正会改变决策的像素上，用 semantic / frequency / expert evidence 预测 DSM benefit。

**结果**：六分数 gate 失败。

**结论**：当前 benefit predictor 不足以支撑选择性 DSM 主方法。

---

## 4.7 2026-09-23｜D10M 与 D11

### D10M

**目的**：使用保持 amplitude 的空间扰动，判断模型受损到底来自内容变化还是空间结构变化，并尝试 rescue。

**结论**：固定评分 gate 失败，不支持当前配方。

### D11

**目的**：用监督 benefit/harm probe，并在 Val2 外做校准，直接预测 DSM 帮助/伤害。

**结论**：gate 失败；不能建立稳定 benefit/harm predictor。

---

# 5. 2026-09-24 ～ 2026-09-28：更深结构、风险代理、FM/adapter 与独立数据检查

## 5.1 2026-09-24｜D12 deep decoder context / frequency / capacity

**目的**：检查失败是否因为上下文层级、频率表达或模型容量不足。

**结论**：固定 gate 未通过；未证明继续加深 decoder/context/frequency 是主要突破口。

---

## 5.2 2026-09-25｜D13 RGB-anchored DSM residual + risk surrogate

**目的**：让 RGB 做主锚点，只在预测到“DSM 有帮助”时注入 DSM residual，并用风险代理控制负迁移。

**结果**：Stage 1 完成；两 seed gate 失败；Stage 2 跳过。

**结论**：当前 residual/risk 实现不成立，不扩大训练。

---

## 5.3 2026-09-26｜D14 inference-only DSM sensitivity

**目的**：固定 D13 head，不再训练，只改变 DSM 内容，确认模型是否真的对 DSM 内容敏感。

**结论**：发现 sensitivity，但没有形成 benefit gate；“模型会响应 DSM”不等于“知道什么时候该使用 DSM”。

---

## 5.4 2026-09-27｜D16 / D17

**目的**：
- D16：intervention consistency；
- D17：geometry auxiliary supervision；
- 同时加入匹配控制，避免把额外训练信号误认为新机制。

**结果**：16/16 完成，A2/B1 gate 失败。

**结论**：当前 intervention consistency 与 geometry auxiliary 不能建立稳定新增贡献。

---

## 5.5 2026-09-28｜D18 / D19 + seed17 replication

**目的**：引入 frozen-DINO / pretrained adapter 路线，并测试 intervention structures；进行 seed42/17 匹配复验。

**结果**：
- 8/8 完成；
- P2 seed42 成为候选；C2/C3 失败；
- seed17 复验中 P2 两个 seed 均相对同 seed P0/P1 有正增益；
- 但 DSM 完全缺失时 P2 仍比 P0 低约 0.4–0.5 pp。

**结论**：FM/adapter 能给出较稳定 clean 增益线索，但“模态缺失时不降级”的问题仍未解决。

---

## 5.6 2026-09-28｜D20 独立数据源审计

**目的**：寻找独立数据（GAMUS / US3D 等）验证 P2 是否跨地域/跨源稳定。

**结果**：GAMUS 三城市样本内容检查通过，但 HDF5 缺少足够 source/geographic attributes；US3D 使用条件仍需确认；Vaihingen seed42 per-tile gate 未过，因此没有自动启动 seed17。

**结论**：独立数据证据仍不充分；不能把 Val2 双 seed 当成跨地域泛化。

---

# 6. 2026-09-29 ～ 2026-10-04：细粒度频率、适配、保护/恢复与路由机制大规模排查

## 6.1 2026-09-29｜D21 detail-frequency controls

**目的**：把 fine-scale height 与 low/high frequency 做严格匹配对照，在两数据集、两 seed 上判断细节频率是否能同时提高准确性和 missing-DSM safety。

**状态**：32/32 完成并归档。

**结论**：F2 accuracy gate 与 missing-DSM safety gate 均失败；不支持当前 detail-frequency 配方升级主线。

---

## 6.2 2026-09-29 ～ 2026-10-01｜Post-D21 多方向组合

**目的**：系统测试 adaptation、conditional DSM residual、联合 LR 恢复、factorial interaction、混合退化，以及运行吞吐。

**状态**：主 42/42 完成，mixed E 4/4 完成并审计。

**结论**：大量组合提供了机制边界，但没有形成可以直接取代强基线的稳定新主方法；后续转向 frozen expert gating 与训练机制拆解。

---

## 6.3 2026-10-01｜D23 frozen experts + semantic/frequency/utility gate

**目的**：使用冻结专家与语义/频率/效用门控，测试 selective routing 是否能优于强融合。

**结果**：TSF 综合比 M0_safe 低 0.148998 pp；减害的同时也丢失纠错能力。

**结论**：全部预设机制门槛未过；已知 DSM missing 的确定性 fallback 只是工程能力，不能等同研究贡献。

---

## 6.4 2026-10-02｜D24

**目的**：系统比较适配、普通增强、Pair 约束、语义/KD。

**结果**：部分解冻和普通增强是非常强的基线；其中 A1/A3 的 Pair loss 开关实际未启用，因此不能把这两项写成 Pair 机制负结果。

**结论**：修正 Pair 实现后再做 D25；强基线必须保留。

---

## 6.5 2026-10-02｜D25

**目的**：修正 Pair；测试状态分头、完整/缺失不同 head，以及梯度投影/冲突处理。

**结果**：四项预设机制筛选均未过；真实 Pair 已生效，但采样到的梯度不支持“全局梯度冲突”是主要瓶颈。

**结论**：不继续围绕当前 PCGrad/分头配方扩展。

---

## 6.6 2026-10-03｜D26

**目的**：测试双向特征交互、容量控制以及 semantic/frequency shuffle，判断复杂交互是否真正超出普通融合。

**结果**：普通 B0 融合对 RGB 综合 +0.690973 pp；XSF 对 B0 仅 +0.156829 pp，未过增量及双侧保留门槛。

**结论**：复杂双向交互的额外收益不足，普通融合本身是强解释。

---

## 6.7 2026-10-03｜D27

**目的**：保护/恢复、动态专家、全局/局部/类别路由。

**技术插曲**：原队列因 `KeyError treatment` 在 step0 失败，属于技术失败，不算科学负结果；修复后 10/10 完成。

**结果**：保护+恢复相对匹配对照损失约 1.77–1.89 pp；保留更多 DSM 独有正确像素时，又会损失 RGB 原本正确像素。

**结论**：四项机制门槛均未过；确认存在真实的“保护与恢复信息取舍”。

---

## 6.8 2026-10-03｜D28

**目的**：控制相同边际损伤，比较共同受损与独立受损，验证是否需要专门处理“两个模态同时坏”。

**结果**：B0 独立−共同仅 +0.014570 pp，远低于 0.3 pp 门槛。

**结论**：本轮不支持“共同受损”是当前主要特殊问题；原 D29 不触发。

---

## 6.9 2026-10-04｜D30

**目的**：拆解 protection/recovery loss，并比较 area/pixel normalization；同时对固定 checkpoint 做 routing intervention。

**结果**：
- P vs S0：+0.041182 pp；
- R：−2.013409 pp；
- PR_area：−0.064718 pp；
- PR_pixel：−1.291674 pp。

**结论**：四个继续门槛均 False；归一化能减轻损失，但没有建立可归因的新贡献。

---

## 6.10 2026-10-04 ～ 2026-10-05｜Post-D30 A / B / C / F

### A：对齐范围 / 错配 / 权重

**结果**：A2 对 A0 仅 +0.101643 pp，且低于 A1/A3，gate=False。

### B：局部对应 / 增强

**结果**：B3 gate=False。

### C：缺失知识迁移 / 正确掩码 KL

**结果**：C2 双侧门槛 False；普通 C0 已能解释大部分改善，因此不能把收益归功跨模态蒸馏。

### F：条件频率

**状态**：因前置 gate 未过，F0–F3 实际 `SKIPPED_GATE`，不是科学负结果。

**结论**：继续坚持“失败 gate 不救超参/预算”的规则。

---

# 7. 2026-10-05 ～ 2026-10-08：N1/N2/N5/N3/S1 条件互补与缺失支持阶段

## 7.1 2026-10-05｜N1 多深度入口 / partial adaptation

**目的**：判断多深度特征入口是否比末端特征更适合缺失模态适配，以及 partial adaptation 是否能抵消入口损失。

**结果**：
- N1-2（末端 partial adaptation）S_available = 86.239697；
- N1-3（多深度 partial adaptation）= 85.358638；
- N1-3 比 N1-2 低 0.881059 pp；
- 虽然 adaptation 对冻结多深度入口有 +2.789492 pp 修复，但仍未超过匹配末端适应控制。

**结论**：普通 adaptation 有效且是强控制；当前多深度入口没有新增贡献，gate=False。

---

## 7.2 2026-10-05 ～ 2026-10-06｜N2 3×3 relation propagation

**目的**：测试 DSM height→RGB、RGB feature→DSM、双向传播和空间打乱，判断局部跨模态关系是否能解释/修复缺失弱侧。

**状态**：六组完成并独立验收。

**结果**：固定双向候选 gate=False；S 相对空间控制 −0.007028 pp，方向和打乱增量均未达到门槛。

**结论**：关闭当前 3×3 relation 实现的新增贡献承诺，不扫窗口、预算或 seed 挽救。

---

## 7.3 2026-10-05 ～ 2026-10-06｜E0 / E1 / E2 零训练诊断

**目的**：不新增训练，定位 N2/N5/N3 后续问题是否真实存在。

### E0：空间/边界诊断

**发现**：clean Full 边界的伤害率明显高于内部区域，说明边界压力真实存在，但不能证明跨区域传播是因果。

### E1：内容相关缺失

**发现**：RGB 缺失、DSM 高变化区域的 H 规则相对 U 有约 0.65 pp 缺口，两 tile 同号；触发 N5 问题门槛。

### E2：物理缺失 × 标记可靠性

**发现**：RGB 漏报相对硬回退约高 1 pp，误报完整 RGB 可损失约 6.4 pp；DSM 漏报效应小且跨 tile 异号。

**结论**：缺失标记错误的代价方向高度不对称；exact fallback 不等于精度最优。诊断只证明“问题存在”，不是方法有效。

---

## 7.4 2026-10-06｜N5 mixed missingness

**目的**：针对 E1 发现的内容相关缺失，训练四组匹配控制，测试混合缺失/规则是否真正优于普通适应。

**结果**：固定 N5-3 gate=False；T 对随机 N5-1 仅 +0.041878 pp（要求 ≥0.5）；clean / DSM全缺失相对 N5-0 为 −0.191071 / −0.152271 pp，超过保护底线。

**结论**：当前混合缺失配方没有新增贡献；普通 adaptation 仍是强控制。位置相关问题本身没有被否定。

---

## 7.5 2026-10-07｜E3/E4 N5 边界复查与 cross diagnostic

**目的**：确认 N5 失败后，是否仍存在值得训练的新问题：局部上下文、输出/feature 控制、边界构成等。

**关键结果**：
- R1 问题门槛不通过；
- 但 RGB 在固定 feature、C=0 条件下仍表现出 +0.58～1.31 pp 的上下文缺口，两个 tile 同方向；
- DSM 对应信号未通过。

**结论**：支持继续训练验证“保留融合上下文能否帮助 RGB 缺失”，但只是一条 RGB 单向问题线索，不能提前称双向贡献。

---

## 7.6 2026-10-07 ～ 2026-10-08｜N3 + S1 九组

### N3：区域归属 / local vs grid

**目的**：判断真正的条件区域建模是否能超过简单局部/网格控制。

**结果**：N3-4 相对局部 −0.000078 pp、相对网格 +0.001937 pp。

**结论**：增量几乎为零，固定 gate=False；当前区域配方关闭，不换后验候选救结果。

### S1：feature × output 四格 / 保留上下文线索

**目的**：验证 RGB 缺失场景下，保留融合时的上下文 feature 或输出策略是否能产生真实恢复，并检查副作用。

**关键结果**：
- S1-3 RGB 局部 U 相对 S1-0：**+4.102047 pp**，两 tile 同方向；
- DSM：−0.023201 pp，且两 tile 方向不一致；
- worst `aux_shift8 / 3_11`：−0.391546 pp，违反原 −0.2 pp 保护线。

**结论**：
1. S1 给出了目前非常强的 **RGB 单向局部恢复线索**；
2. 但它同时损伤了其他退化条件，因此固定 gate=False；
3. 不能把 +4.10 pp 直接升级为“方法成功”或“双向贡献”；
4. 下一步真正要解决的是：保留这类局部恢复收益，同时通过参数隔离/局部修正避免污染正常和其他退化场景。

---

# 8. 2026-10-08 当前正在执行：Post-S1 Support

**研究问题**：S1 的 +4.102 pp 到底来自什么？能否保留 RGB 缺失/局部恢复收益，同时消除 aux_shift8 等保护失败？

## D0（0 训练）

复用现有预测并拼接，建立“完全不训练新网络”能达到的上限/对照。

## D1（0 训练）

固定同一权重，比较不同策略，区分：
- inference routing 问题；
- training-induced parameter contamination 问题。

## P0–P9（10 × 8000 新 step）

统一从 S1-0 selected8000 state 出发，seed42；围绕三类变量做 2×2×2 配对：
- 共享更新 vs 冻结基座 / 参数隔离；
- 仅 mask vs 保留上下文；
- 全域修正 vs 局部修正；
另有 P8 空间打乱、P9 简单 logit/mask calibration 机制控制。

**P7** 为实验前冻结的主候选：`冻结基座 + 保留上下文 + 局部修正`，不是跑完后再挑最好结果。

## E（0 训练）

六类压力条件，对 P 系列和对照做统一 robustness 检验。

## Q

DSM 镜像方向四组仅条件储备，当前不可自动运行；只有固定 DSM 证据和 P7 资格同时满足后才能另立协议。

**截至 commit `8cb04ac456296b72d7c8302745c25f18b60c4ea2` 的真实状态**：
- 2026-10-08 23:53（UTC+8）controller LIVE；
- 阶段 `PREPARING_D0_MASKS`；
- D0 CPU 正在处理 `3_11 / rgb_U`；
- D1、P0–P9、E 全部 PENDING；
- 尚无 GPU 首步和新的科学结果；
- 只允许物理 GPU0，FIFO 单 worker；
- 不能把“队列已登记/CPU 正在准备”写成训练已完成或方法已有效。

---

# 9. 当前已经可以确定的研究结论

1. **clean Optical+DSM 可以优于 true Optical-only，但双流容量是强混淆因素。** 任何“DSM 带来全部 clean 增益”的表述都不成立。
2. **harmful fusion 是真实问题。** clean DSM 有益，但 down8 / zero 等严重退化会使双模态模型低于真实 Optical-only。
3. **普通 robustness baseline 很强。** corruption training 对轻中度退化有效，modality dropout 对完全缺失有效，因此新方法必须超过这些控制，而不能只比 clean baseline。
4. **简单 confidence / entropy / HF reliability / benefit predictor 不能稳定决定什么时候相信 DSM。** 多轮 gate 都未达到预设标准。
5. **Rare30 有训练分布价值，但不等于可靠性机制。**
6. **Optical 与 DSM 的频率性质确实不同。** DSM physical-frequency 是有价值的机制证据，但没有成为后续最终主线。
7. **普通 adaptation、普通融合、部分解冻往往是强基线。** 很多复杂模块的收益最终能被这些简单控制解释。
8. **保护 RGB 已有正确预测与恢复 DSM/RGB 缺失信息之间存在真实 trade-off。** D27/D30 等多轮实验反复出现这一现象。
9. **当前最强的新线索是 S1 的 RGB 单向局部恢复 +4.102047 pp。** 但因为其他条件保护失败，它只能视为“值得解释和隔离的现象”，不是已通过 gate 的方法。
10. **当前研究主线已经转成：条件互补 + 缺失/退化支持 + 参数隔离 + 局部修正。** 频率研究作为历史机制证据和潜在 cue 保留，不再单独主导当前训练队列。

---

# 10. 已明确停止 / 降级的路线

- 继续在 decoder 堆频率模块；
- crop256；
- History30 / Rare15+History15；
- Normal/HF shallow detail；
- 把原 HF gate 直接解释成 modality-quality reliability；
- 当前 Reliability-v2 作为主方法；
- 当前 3×3 relation propagation（N2）；
- 当前 mixed missingness N5 配方；
- 当前 N3 区域实现；
- 当前 D23/D25/D27/D30 gate/routing/loss 实现；
- 失败后通过扫更多超参、seed、预算“救 gate”的做法。

技术失败但不能当科学负结果：
- D27 原始队列 `KeyError treatment`；修复后结果另算。

条件未满足而没有运行，不能当负结果：
- D22 原草案（被替代，未运行）；
- D10 selective DSM benefit 正式训练（设计冻结但独立源未满足）；
- Post-D30 F（SKIPPED_GATE）；
- Q 镜像 DSM 当前储备组。

---

# 11. 当前证据边界

- 大量近期实验仍以 Potsdam `fit12 / Val2=3_11,5_10`、seed42 为开发证据；
- NoBoundary `mIoU_fg5` 是主要口径，FullGT 多用于诊断；
- 两个 Val tile 不能当统计独立样本或跨地域泛化；
- Test6 / held4 / independent final 未在当前开发队列中自动使用；
- 只有最终值得保留的候选才应追加 seed 和独立数据确认；
- GitHub 保存轻量原件/审计/配置，checkpoint、影像、预测等大文件仍主要留在服务器。

---

# 12. 后续阅读入口

优先顺序：

1. `docs/START_HERE.md`
2. `docs/current/RESEARCH_DECISION.md`
3. `docs/current/HANDOFF.md`
4. `docs/current/PROJECT_STATUS.md`
5. `docs/current/NEXT_EXPERIMENT.md`
6. 本文件 `docs/experiments/ALL_EXPERIMENTS_TIMELINE_20261008.md`
7. `docs/experiments/rebuild_v1/INDEX.md`
8. 各实验原始报告与 `records/` 轻量证据

历史频率阶段的完整原记录：
`docs/archive/legacy/EXPERIMENT_MASTER_LEGACY_20260918.md`。

---

最后更新：2026-10-08。
