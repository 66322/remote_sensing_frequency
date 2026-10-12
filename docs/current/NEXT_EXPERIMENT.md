# 下一实验（当前：DESIGN_REVIEW_NOT_REGISTERED）

当前没有已授权、已登记或后台等待的新实验。Post-T paired v2 与 Structured Failure v0.1 都已完成独立科学验收；两轮均不触发自动后继。

## 已关闭的问题

- **训练预算线**：F/H/R 从 8k 延长到 16k 的固定端点变化分别约 +0.001 / +0.091 / -0.016 pp，继续加步数没有依据。
- **Structured-location vulnerability 线**：S1 主 PE 只有 +0.123 pp，固定结论 `NO_SUPPORT_THIS_PROTOCOL`，不扩 20→40、不改 mask 追正。
- **naive context rescue**：同权重 `M000_context` 比 `M000_masked` 在四类缺失族下都明显更差，不继续作为正向候选。

结果分别见：

- [Post-T paired v2 结果](../experiments/POST_T_PAIRED_V2_RESULTS_20261012.md)
- [Structured Failure v0.1 结果](../experiments/STRUCTURED_FAILURE_V0_RESULTS_20261012.md)

## 下一单一研究问题

优先设计：**模态可靠性估计 + 条件路由/抑制**。

问题表述：

> 当 RGB 或 DSM 的质量局部或整体下降时，模型能否仅根据部署时可获得的信息识别当前不可靠模态，并降低该模态对融合结果的负作用，同时保留正常双模态输入下的互补收益？

这比继续增加训练时间或再开放 encoder 更贴合现有证据：S1 已经能显著降低 RGB 缺失伤害，但错误的 context/routing 又会把损伤放大。

## 新协议应至少包含

1. **可靠性信号**：明确来自输入统计、特征一致性、预测不确定性或跨模态一致性中的哪一种；推理时不得依赖 GT。
2. **双向退化**：RGB 与 DSM 都覆盖 local missing、global missing、blur/downsample/noise/shift 等固定家族，避免只做单向鲁棒性。
3. **严格对照**：同权重/同容量优先；若新增参数，另做 capacity-matched 对照，避免把容量收益误写成可靠性收益。
4. **clean 保护**：正常输入性能必须有明确下限，同时看退化条件的 pooled 与 worst-tile 收益。
5. **机制统计**：按类别、missing/healthy 区域、退化强度和路由权重/可靠性分数统计，验证机制是否真的随质量变化。
6. **停止条件**：开发门槛提前冻结；若核心信号不存在，停止该线而不是追加 seed/改门槛。
7. **数据隔离**：当前仍只用开发划分；Test6/held4/final 保持关闭，直到方法与协议完全冻结。

## 现在不要做

不要启动 GPU；不要继续 Post-T 步数；不要重新跑 Structured v0；不要追加 realization/seed；不要扫 encoder block 数量；不要直接训练尚未定义的 reliability 模块；不要启用 Test6/held4/final。

只有新的设计文档明确写出问题、假设、输入可靠性定义、对照、预算、门槛和停止条件，并由用户显式决定执行后，才登记下一队列。
