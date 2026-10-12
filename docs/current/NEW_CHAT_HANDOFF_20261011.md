# 新对话交接：Structured Phase1A 已完成、上传并验收

截至 2026-10-12，权威分支 `rebuild-v1-protocol-20260915` 已完成 Post-T paired v2 及其固定零训练 Structured Failure v0.1 后继。当前**没有运行中或自动等待的新实验**。

## 先读

1. [RESEARCH_DECISION.md](RESEARCH_DECISION.md)：当前研究结论与主线。
2. [PROJECT_STATUS.md](PROJECT_STATUS.md)：服务器/实验阶段状态。
3. [NEXT_EXPERIMENT.md](NEXT_EXPERIMENT.md)：当前为 `DESIGN_REVIEW_NOT_REGISTERED`，不要直接开 GPU。
4. [Structured Failure v0.1 结果](../experiments/STRUCTURED_FAILURE_V0_RESULTS_20261012.md)：最新机制诊断的完整人工验收。

## 最新 Structured 证据

GitHub 原件提交：`fad186bece5170140f14f7b4e643ff3d102f1424`。

目录：`records/research_structured_failure_v0_20261012T073410_81887/evidence_20261012T164118006539_357012/`。

技术状态：42/42 COMPLETE，0 RUNNING/PENDING/TECHNICAL_FAILURE；640 missing + 8 clean + 6 endpoint checks；0 optimizer updates；无自动 Phase1B/Phase2/20→40。

固定科学 gate：**NO_SUPPORT_THIS_PROTOCOL**。

## 最新结论摘要

S1 主 `PE=D(gradient)-D(matched)=+0.123 pp`，95% CI [-0.308,+0.593]，两个 tile 的平均 PE 都未为正，no-Car 和类别支持条件也失败，因此不支持“S1 对高梯度/结构位置 RGB 缺失有稳定额外脆弱性”。

但 RGB-only 的 PE 为 +3.119 pp 且 20/20 realization 为正；S1 的 absolute missing damage 约 21 pp，相比 RGB-only 约 56–62 pp 大幅下降。这使“DSM/双模态在 RGB 退化时提供条件互补”成为更强线索。

同权重 `M000_context` 比 `M000_masked` 在四类 mask 下差约 11–18 pp，因此当前 naive context route 不应继续作为正向候选。

## 研究纪律

不要为追正结果改 mask、扩 realization、追加 seed 或换 checkpoint；不要加载 Test6/held4/final；不要从旧控制器启动任何后继。

下一步先审阅 Post-T paired v2 原件，与本轮结果合并后，再冻结一个围绕**模态可靠性/路由**的单一问题。新的训练或诊断必须另有设计文档和显式登记。
