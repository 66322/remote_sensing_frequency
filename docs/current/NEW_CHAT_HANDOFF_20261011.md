# 新对话交接：Post-T 与 Structured 两轮均已完成科学验收

截至 2026-10-12，权威分支 `rebuild-v1-protocol-20260915` 已完成并审阅 Post-T paired v2 与 Structured Failure v0.1。当前**没有运行中、已登记或自动等待的新实验**，状态为 `DESIGN_REVIEW_NOT_REGISTERED`。

## 先读

1. [RESEARCH_DECISION.md](RESEARCH_DECISION.md)：当前联合研究结论与主线。
2. [PROJECT_STATUS.md](PROJECT_STATUS.md)：两轮最新实验状态与关键数值。
3. [NEXT_EXPERIMENT.md](NEXT_EXPERIMENT.md)：下一 reliability/routing 设计要求；当前不要直接开 GPU。
4. [Post-T paired v2 结果](../experiments/POST_T_PAIRED_V2_RESULTS_20261012.md)：F/H/R 8k/16k 配对训练独立验收。
5. [Structured Failure v0.1 结果](../experiments/STRUCTURED_FAILURE_V0_RESULTS_20261012.md)：固定结构化缺失机制诊断验收。

## Post-T paired v2

原件提交：`0283f74e6c8242694737ea75faa225c8af60a8c2`。权威总判定：**PAIRED_SCREEN=False / NO_FURTHER_DISPATCH**。

固定 RGB_U 端点：F8 83.8566 / H8 84.4411 / R8 84.8964；F16 83.8579 / H16 84.5318 / R16 84.8804。8k→16k 分别只有 +0.001 / +0.091 / -0.016 pp，因此关闭“训练不够久”解释。R/H 明显优于 F，说明 RGB 专家接口参与适应是有价值线索；R 相对 H 只有约 +0.349 pp 且完整 screen 未通过，不把最后 4 个 encoder block 写成已验证贡献。

R16 冻结 digest 与 support 外 native 输出保护正常，负总判定属于科学 gate，不是实现损坏。

## Structured Failure v0.1

原件提交：`fad186bece5170140f14f7b4e643ff3d102f1424`。

技术状态：42/42 COMPLETE，640 missing + 8 clean + 6 endpoint checks，0 optimizer updates。固定结论：**NO_SUPPORT_THIS_PROTOCOL**。

S1 主 PE = +0.123 pp，95% CI [-0.308,+0.593]，不支持“S1 对高梯度/结构位置 RGB 缺失有稳定额外脆弱性”。但 RGB-only PE = +3.119 pp 且 20/20 realization 为正；S1 absolute missing damage 约 21 pp，相比 RGB-only 约 56–62 pp 大幅下降，说明双模态/DSM 对 RGB 退化存在明显补偿线索。

同权重 `M000_context` 比 `M000_masked` 在四类 mask 下差约 11–18 pp，因此当前 naive context route 失败。

## 联合研究判断

当前更值得研究的问题是：

> **RGB 或 DSM 质量变化时，模型如何估计每一路当前是否可信，并条件性利用或抑制模态信息，使双模态补偿得到保留而错误路由不再放大损伤？**

所以下一优先方向是**模态可靠性估计 + 条件路由/抑制**，不是继续加步数、扫更多 encoder block、修改 Structured mask 追正或继续堆频率模块。

## 研究纪律

不要为追正结果改门槛、改 mask、扩 realization、追加 seed 或后验换 checkpoint；不要自动进入 Structured Phase1B/Phase2；不要加载 Test6/held4/final；不要从旧控制器启动任何后继。

新的训练或诊断必须先有独立冻结设计，至少包含 RGB/DSM 双向退化、部署可得可靠性信号、同权重或 capacity-matched 对照、clean 保护、退化收益、机制统计和停止条件，并由用户显式决定后再登记。
