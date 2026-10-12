# 当前研究决定（2026-10-12）

## 主线

研究主线保持为：**RGB–DSM 条件互补与模态退化/缺失鲁棒性**。任务驱动恢复仍为旁支；频率堆叠不是当前优先方向。

## Structured Failure v0.1 的决定

本轮固定 Phase1A 已完成并验收，结论为 **NO_SUPPORT_THIS_PROTOCOL**。详见 [Structured Failure v0.1 结果](../experiments/STRUCTURED_FAILURE_V0_RESULTS_20261012.md)。

冻结主假设“S1 对高梯度/结构位置 RGB 缺失存在可重复的额外脆弱性”不成立：主 PE 仅 +0.123 pp，两个 tile 的平均 PE 均未为正，no-Car 与类别支持条件也未建立。因此关闭该假设，不通过增加 realization、seed、改变 mask 或换 checkpoint 追正结果。

但本轮保留三个有价值的研究事实：

1. RGB-only 存在强而稳定的结构位置敏感性（PE +3.119 pp，20/20 realization 为正）。
2. S1 的绝对缺失损伤远低于 RGB-only，说明 DSM/双模态融合对 RGB 退化具有明显补偿线索。
3. 同权重 `M000_context` 在四类 mask 下均显著差于 `M000_masked`，当前 context 路由不是可推进的正向方案。

## 对后续研究的含义

下一阶段不再问“能否证明 S1 有 structured-location failure”，而应问：

**当某一模态退化或缺失时，融合模型如何识别不可靠信息，并在保留互补收益的同时避免错误路由/错误上下文放大损伤？**

这与当前“模态可靠性”主线一致，也能解释本轮同时出现的两件事：S1 可以显著抵抗 RGB-only 的缺失伤害，但 naive context 路由又会严重恶化。

## 与 Post-T paired v2 的关系

Structured Failure 不回溯改变 Post-T F/H/R 的冻结候选、保护门槛或 checkpoint 选择。Post-T paired v2 已有独立上传原件，必须先单独科学验收，再与本轮机制诊断合并决定下一实验。

## 当前执行决定

- Structured Failure Phase1A：**CLOSED**。
- 20→40：**禁止自动扩展**。
- Phase1B / Phase2：**不派发**。
- 新 seed / 新训练：**不派发**。
- Test6 / held4 / final：**保持关闭**。
- 下一实验：**DESIGN_REVIEW_NOT_REGISTERED**，没有后台队列、没有 GPU 任务。
