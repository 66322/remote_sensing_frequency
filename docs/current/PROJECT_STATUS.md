# 当前项目状态（2026-10-12 结构化诊断已收口）

权威分支：`66322/remote_sensing_frequency` / `rebuild-v1-protocol-20260915`。

## 当前运行状态

Structured Failure v0.1 已技术完成：42/42 COMPLETE，0 RUNNING，0 PENDING，0 TECHNICAL_FAILURE，controller/worker 已退出；GPU0/GPU1 已空闲。该阶段为固定零训练诊断，optimizer updates = 0。

轻量原件已上传到提交 `fad186bece5170140f14f7b4e643ff3d102f1424`：
`records/research_structured_failure_v0_20261012T073410_81887/evidence_20261012T164118006539_357012/`。

人工科学验收见：[Structured Failure v0.1 结果](../experiments/STRUCTURED_FAILURE_V0_RESULTS_20261012.md)。固定 gate = **NO_SUPPORT_THIS_PROTOCOL**，Phase1A 已关闭，不自动派发任何后继。

## 当前最重要结果

- S1 主 `PE = D(gradient)-D(matched) = +0.123 pp`，95% CI [-0.308, +0.593]，低于预先冻结的 0.15 pp no-support 门槛。
- 两张 tile 的平均 PE 分别为 -0.062 / -0.083 pp；`PE_no_car=-0.553 pp`；五类只有 3/5 平均 PE 为正，结构化脆弱性假设未成立。
- RGB-only 的 PE = +3.119 pp，95% CI [2.831, 3.402]，20/20 realization 为正，说明诊断本身能暴露 RGB 单模态的结构敏感性。
- S1 四类 mask 的绝对缺失区 damage 约 21 pp，而 RGB-only 约 56–62 pp；当前更强线索是 DSM/双模态融合显著削弱 RGB 缺失伤害。
- 同权重 `M000_context` 相对 `M000_masked` 的 CB 在四族均为负（约 -11.4 至 -18.5 pp），当前 context 路由不能作为成功救援方案。

## 当前研究主线

继续保持：**RGB–DSM 条件互补 + 模态退化/缺失鲁棒性**。Structured Failure 是已关闭的诊断分支，不再追求把 S1 的 structured-location vulnerability 做成正结论。

此前 Post-T paired v2 的 F/H/R 训练与其冻结候选/保护门槛不因本轮结果重新选择；其科学结论需独立验收后再与本轮合并。

## 当前禁止事项

不自动 20→40；不启动 Phase1B/Phase2；不追加 seed；不改 mask 后重跑；不因本轮结果重新挑 checkpoint；不加载 Test6/held4/final；不启动新训练。

## 立即下一步

当前服务器**无需执行新实验命令**。下一步是独立审阅已上传的 Post-T paired v2 原件，并把它与本轮结果合并成下一研究问题；新的 GPU 实验必须先另写冻结设计、再显式登记。
