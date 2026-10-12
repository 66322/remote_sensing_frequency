# 当前交接（2026-10-12，两轮最新实验均已收口）

权威分支：`rebuild-v1-protocol-20260915`。

## 一句话状态

Post-T paired v2 与 Structured Failure v0.1 都已经完成、上传并独立科学验收。Post-T 总 gate = **PAIRED_SCREEN=False**；Structured gate = **NO_SUPPORT_THIS_PROTOCOL**。当前没有自动后继实验或 GPU 队列，状态为 **DESIGN_REVIEW_NOT_REGISTERED**。

## Post-T paired v2

- 原件提交：`0283f74e6c8242694737ea75faa225c8af60a8c2`
- 人工验收：[POST_T_PAIRED_V2_RESULTS_20261012.md](../experiments/POST_T_PAIRED_V2_RESULTS_20261012.md)
- 固定端点：F8 83.8566 / H8 84.4411 / R8 84.8964；F16 83.8579 / H16 84.5318 / R16 84.8804。
- 8k→16k 只有 +0.001 / +0.091 / -0.016 pp：关闭“训练不够久”解释。
- R/H > F，说明 RGB 专家接口参与适应是有效线索；R-H 只有约 +0.349 pp 且完整 screen 未通过，不把最后 4 encoder block 写成已验证贡献。
- R16 技术冻结/保护正常；总 gate=False 是科学判定而非实现损坏。

## Structured Failure v0.1

- 原件提交：`fad186bece5170140f14f7b4e643ff3d102f1424`
- evidence：`records/research_structured_failure_v0_20261012T073410_81887/evidence_20261012T164118006539_357012/`
- 人工验收：[STRUCTURED_FAILURE_V0_RESULTS_20261012.md](../experiments/STRUCTURED_FAILURE_V0_RESULTS_20261012.md)
- 42/42 COMPLETE，640 missing + 8 clean + 6 endpoint checks，0 optimizer updates。
- S1 主 PE = +0.123 pp，95% CI [-0.308,+0.593]：不支持 S1 的高梯度/结构位置额外脆弱性。
- RGB-only PE = +3.119 pp，20/20 realization 为正：诊断有效，单模态 RGB 的结构敏感性真实存在于本协议。
- S1 absolute missing damage 约 21 pp，RGB-only 约 56–62 pp：DSM/双模态补偿是更强线索。
- `M000_context` 比同权重 `M000_masked` 差约 11–18 pp：当前 naive context route 失败。

## 联合研究结论

现有证据更支持下面的问题：

> **融合模型在 RGB/DSM 质量变化时，需要判断哪一路模态当前可信，并条件性地使用或抑制信息；双模态本身有补偿能力，但错误路由会把这种优势变成损伤。**

因此下一优先方向是**模态可靠性估计 + 条件路由/抑制**，而不是继续加训练时间、扫更多 encoder block、修改 Structured mask 追正或堆频率模块。

## 不要误读

- 两轮主要仍是 Potsdam Val2 开发证据，不能写成独立地域或最终测试结论。
- Structured 的 20 个 mask realization 不是 20 个训练 seed/独立场景。
- Post-T 的 F/H/R 可训练容量不同，R-H 仍有容量混杂可能。
- `PAIRED_SCREEN=False` 和 `NO_SUPPORT_THIS_PROTOCOL` 都是科学负/不充分结果，不是技术失败；不要后验改门槛。

## 当前下一步

服务器**无需执行任何新命令**。先设计 reliability/routing 新协议：覆盖 RGB/DSM 双向退化、部署可得可靠性信号、同权重或 capacity-matched 对照、clean 保护、退化收益、机制统计、提前冻结门槛与停止条件。用户显式决定后再登记实验。

读取顺序：[RESEARCH_DECISION](RESEARCH_DECISION.md) → [PROJECT_STATUS](PROJECT_STATUS.md) → [NEXT_EXPERIMENT](NEXT_EXPERIMENT.md) → [Post-T 结果](../experiments/POST_T_PAIRED_V2_RESULTS_20261012.md) → [Structured 结果](../experiments/STRUCTURED_FAILURE_V0_RESULTS_20261012.md)。
