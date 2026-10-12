# 当前交接（2026-10-12 16:xx，Structured Phase1A 已收口）

权威分支：`rebuild-v1-protocol-20260915`。

## 一句话状态

Post-T paired v2 已完成并上传；其固定零训练后继 Structured Failure v0.1 也已 42/42 技术完成、上传并科学验收。Structured 主 gate = **NO_SUPPORT_THIS_PROTOCOL**，当前没有自动后继实验或 GPU 队列。

## Structured 权威证据

- 服务器目录：`research_structured_failure_v0_20261012T073410_81887`
- 轻量证据提交：`fad186bece5170140f14f7b4e643ff3d102f1424`
- evidence：`records/research_structured_failure_v0_20261012T073410_81887/evidence_20261012T164118006539_357012/`
- 人工结果验收：[STRUCTURED_FAILURE_V0_RESULTS_20261012.md](../experiments/STRUCTURED_FAILURE_V0_RESULTS_20261012.md)

42 个任务全部 COMPLETE，0 RUNNING/PENDING/TECHNICAL_FAILURE；640 missing + 8 clean + 6 endpoint checks；optimizer updates=0。上传后 `summary.json` 已按 exact wrapper 解码并核对原始 SHA256。

## Structured 科学结论

- S1 主 PE = **+0.123 pp**，95% CI [-0.308, +0.593]；低于 0.15 pp no-support 门槛。
- 两 tile 平均 PE 均略负，PE_no_car 为负，只有 3/5 类平均 PE 为正：结构位置脆弱性假设不成立。
- RGB-only PE = **+3.119 pp**，20/20 realization 为正：诊断能暴露 RGB-only 的结构敏感性。
- S1 的 absolute missing damage 约 21 pp，RGB-only 约 56–62 pp：DSM/双模态补偿是更强机制线索。
- `M000_context` 相对 `M000_masked` 在四族均差约 11–18 pp：当前 context 路由不能作为成功方案。

## 不要误读

本轮只有两个重复使用的 Potsdam Val2 tile，20 个 mask realization 不是训练 seed 或独立场景；没有 Test6/final。不能把本轮写成跨地域泛化或最终测试结论。

`NO_SUPPORT_THIS_PROTOCOL` 不是技术失败，而是预注册假设在有效实验下没有获得支持；不应通过改 mask、扩 20→40、加 seed 或换 checkpoint 追正。

## 下一步

先独立审阅 Post-T paired v2 原件，再与 Structured 结果联合冻结下一问题。当前优先研究问题转向：**模态退化时如何可靠估计/路由 RGB 与 DSM，避免错误融合或上下文放大损伤，同时保留 clean 双模态收益。**

当前状态：`DESIGN_REVIEW_NOT_REGISTERED`。服务器无需执行新命令。

读取顺序：[RESEARCH_DECISION](RESEARCH_DECISION.md) → [PROJECT_STATUS](PROJECT_STATUS.md) → [NEXT_EXPERIMENT](NEXT_EXPERIMENT.md) → [Structured 结果](../experiments/STRUCTURED_FAILURE_V0_RESULTS_20261012.md)。
