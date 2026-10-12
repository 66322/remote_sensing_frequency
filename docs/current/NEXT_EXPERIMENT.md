# 下一实验（当前：DESIGN_REVIEW_NOT_REGISTERED）

当前没有已授权、已登记或后台等待的新实验。Structured Failure v0.1 已完成并以 `NO_SUPPORT_THIS_PROTOCOL` 收口；禁止从该控制器自动进入 Phase1B/Phase2、扩展 20→40 或启动训练。

## 先完成的工作

1. 独立验收 Post-T paired v2 已上传轻量原件，核对 F/H/R 8k/16k 的 clean、退化保护、R0 差距与内容诊断。
2. 与 [Structured Failure v0.1 结果](../experiments/STRUCTURED_FAILURE_V0_RESULTS_20261012.md) 合并解释：RGB-only 有强结构敏感性；S1 显著削弱 RGB 缺失 damage；同权重 naive context 路由反而恶化。
3. 在上述两轮事实基础上重新冻结一个单一研究问题，再写新的执行协议和 known-answer checks。

## 优先候选问题（尚未批准为实验）

优先考虑**模态可靠性/路由**：在 RGB 或 DSM 局部/整体退化时，模型怎样估计该模态当前是否可信，并抑制会放大损伤的融合或上下文路径，同时保留 clean 条件下的双模态收益。

下一设计应避免把“更多模块”本身当贡献，至少要求：同权重或严格配对对照、clean 性能保护、退化条件下的明确收益、按类别/区域的机制统计，并在开发阶段与最终测试阶段之间保持数据隔离。

## 现在不要做

不要启动 GPU；不要重跑 Structured v0；不要追加 realization/seed；不要改 mask 追正；不要启用 Test6/held4/final；不要直接训练新的 reliability 模块。

只有新的设计文档明确写出问题、假设、对照、预算、门槛和停止条件，并由用户显式决定执行后，才登记下一队列。
