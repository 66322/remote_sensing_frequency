# 当前项目状态（2026-10-12，两轮最新实验均已科学收口）

关键原件复核补充（2026-10-12）：2026-10-12关键原件复核补充：R16−H16=+0.348562pp，两tile分别+0.328642/+0.356335pp，原screen中这一配对passed=True；R16总gate=False的直接原因是六E相对R0的五项底线失败，不是R−H配对未过。F/H/R独立8k/16k预算比较未通过收益门槛；R16自身8k→16k轨迹仍+0.618217pp，因此只关闭当前配方下盲目延长预算的依据，不宣称后半程不学习或普遍收敛。DSM特征内容干预是已存在的更直接线索：R16在块缺失条件C−Z=+4.009563pp、C−S=+9.114377pp；仍是固定模型推理敏感性，不是同预算RGB-only配对训练因果结论。

详见[本次复核](../experiments/LATEST_RESULTS_KEY_REVIEW_20261012.md)。此前“关闭训练不够久”仅针对本轮独立预算方案；R−H局部门槛通过，不等于全screen成功。下一可靠性/路由仍是待设计候选。

权威分支：`66322/remote_sensing_frequency` / `rebuild-v1-protocol-20260915`。

## 当前运行状态

服务器当前没有需要继续运行的已登记实验。Post-T paired v2 与 Structured Failure v0.1 都已完成、上传并完成科学验收；当前状态为 **DESIGN_REVIEW_NOT_REGISTERED**。没有自动后继队列，不应启动新的 GPU 任务。

### Post-T paired v2

轻量原件提交：`0283f74e6c8242694737ea75faa225c8af60a8c2`。

人工科学验收见：[Post-T paired v2 结果](../experiments/POST_T_PAIRED_V2_RESULTS_20261012.md)。权威总判定为 **PAIRED_SCREEN=False / NO_FURTHER_DISPATCH**，因此不能把 R16 写成完整验证成功方法。

核心结果：

- 固定 RGB_U 端点：F8 83.8566，H8 84.4411，R8 84.8964；F16 83.8579，H16 84.5318，R16 84.8804。
- 8k→16k：F +0.0013 pp，H +0.0907 pp，R -0.0160 pp。**继续加训练预算不是收益来源。**
- 16k 下 R-F +1.0225 pp，R-H +0.3486 pp，H-F +0.6739 pp。只训练融合解码器 F 明显不足，RGB 专家接口参与适应更重要；但 R 相对 H 的额外深层尾块收益只有约 0.35 pp，且完整 paired screen 未通过，不能单独宣称已验证。
- R16 冻结参数 digest 与 support 外 native 输出保护通过；总 gate=False 是科学门槛问题，不是实现破坏。

### Structured Failure v0.1

轻量原件提交：`fad186bece5170140f14f7b4e643ff3d102f1424`。

人工科学验收见：[Structured Failure v0.1 结果](../experiments/STRUCTURED_FAILURE_V0_RESULTS_20261012.md)。42/42 COMPLETE，0 RUNNING/PENDING/TECHNICAL_FAILURE，optimizer updates=0；固定 gate = **NO_SUPPORT_THIS_PROTOCOL**。

核心结果：

- S1 主 `PE = D(gradient)-D(matched) = +0.123 pp`，95% CI [-0.308,+0.593]，不足以支持“S1 对高梯度/结构位置 RGB 缺失有稳定额外脆弱性”。
- RGB-only PE = +3.119 pp，20/20 realization 为正，说明结构化诊断本身有效。
- S1 四类 mask 的 absolute missing damage 约 21 pp，而 RGB-only 约 56–62 pp；**DSM/双模态融合显著削弱 RGB 缺失伤害**是更强线索。
- 同权重 `M000_context` 相对 `M000_masked` 的缺失区收益在四族均强负（约 -11.4 至 -18.5 pp），当前 naive context 路由不能作为成功方案。

## 两轮合并后的研究判断

可以关闭两条解释：

1. “目前效果不够只是因为训练时间不足”——Post-T paired 已否定。
2. “S1 的主要弱点就是高梯度/结构位置 RGB 缺失”——Structured v0.1 未支持。

更一致的现象是：**双模态模型确实能在 RGB 退化时获得 DSM 补偿，但错误的融合/上下文路由又可能显著放大损伤。** 因此主线收敛到：

> **模态可靠性估计 + 条件路由/抑制：当 RGB 或 DSM 质量变化时，模型如何判断哪一路当前可信，并只利用可靠互补信息，同时保护 clean 性能。**

## 当前禁止事项

不继续盲目加训练步数；不自动 20→40；不启动 Structured Phase1B/Phase2；不追加 seed；不改 mask 追正；不后验换 checkpoint；不直接扫更多 encoder block；不加载 Test6/held4/final；不启动未冻结的新训练。

## 立即下一步

当前服务器**无需执行任何新实验命令**。下一步是为“模态可靠性/条件路由”写一个新的、单一问题的冻结设计：明确可靠性信号、同权重/严格配对对照、RGB 与 DSM 双向退化、clean 保护、退化收益门槛、停止条件和开发/最终测试隔离。完成设计评审并由用户显式决定后，才登记下一队列。
