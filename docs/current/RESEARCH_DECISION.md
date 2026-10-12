# 当前研究决定（2026-10-12，两轮最新实验已联合验收）

关键原件复核补充（2026-10-12）：2026-10-12关键原件复核补充：R16−H16=+0.348562pp，两tile分别+0.328642/+0.356335pp，原screen中这一配对passed=True；R16总gate=False的直接原因是六E相对R0的五项底线失败，不是R−H配对未过。F/H/R独立8k/16k预算比较未通过收益门槛；R16自身8k→16k轨迹仍+0.618217pp，因此只关闭当前配方下盲目延长预算的依据，不宣称后半程不学习或普遍收敛。DSM特征内容干预是已存在的更直接线索：R16在块缺失条件C−Z=+4.009563pp、C−S=+9.114377pp；仍是固定模型推理敏感性，不是同预算RGB-only配对训练因果结论。

详见[本次复核](../experiments/LATEST_RESULTS_KEY_REVIEW_20261012.md)。此前“关闭训练不够久”仅针对本轮独立预算方案；R−H局部门槛通过，不等于全screen成功。下一可靠性/路由仍是待设计候选。

## 主线

研究主线保持为：**RGB–DSM 条件互补与模态退化/缺失鲁棒性**。下一阶段进一步收敛到：**模态可靠性估计 + 条件路由/抑制**。任务驱动恢复仍为旁支；频率模块堆叠、盲目延长训练或继续扩大 encoder 解冻范围都不是当前优先方向。

## Post-T paired v2 的决定

人工验收见：[Post-T paired v2 结果](../experiments/POST_T_PAIRED_V2_RESULTS_20261012.md)。权威总判定：**PAIRED_SCREEN=False / NO_FURTHER_DISPATCH**。

固定端点显示 R/H 均明显好于 F，说明 RGB 专家接口参与适应比“只训练融合解码器”更有价值。但 8k→16k 对 F/H/R 的增益分别只有 +0.001/+0.091/-0.016 pp，因此**关闭“训练不够久”解释**。R16 相对 H16 只有约 +0.349 pp，且完整 paired screen 未通过，不把最后 4 个 encoder block 的开放写成已验证独立贡献。

R16 的冻结 digest 与 support 外 native 输出保护正常；负总判定属于科学 gate，而不是技术实现破坏。

## Structured Failure v0.1 的决定

人工验收见：[Structured Failure v0.1 结果](../experiments/STRUCTURED_FAILURE_V0_RESULTS_20261012.md)。固定结论为 **NO_SUPPORT_THIS_PROTOCOL**。

冻结主假设“S1 对高梯度/结构位置 RGB 缺失存在稳定额外脆弱性”不成立：主 PE 仅 +0.123 pp，两个 tile 的平均 PE 均未为正，no-Car 与类别支持也未建立。因此关闭该假设，不通过增加 realization、seed、改变 mask 或换 checkpoint 追正。

但保留三个有价值事实：

1. RGB-only 存在强而稳定的结构位置敏感性（PE +3.119 pp，20/20 realization 为正）。
2. S1 的 absolute missing damage 约 21 pp，远低于 RGB-only 的约 56–62 pp，说明 DSM/双模态融合对 RGB 退化具有明显补偿线索。
3. 同权重 `M000_context` 在四类 mask 下均显著差于 `M000_masked`，当前 naive context route 会放大损伤，不能作为正向候选。

## 两轮联合解释

当前最一致的问题不再是“是否训练足够久”或“能否证明 S1 有特殊结构位置故障”，而是：

> **当 RGB 或 DSM 局部/整体退化时，融合模型怎样判断当前模态是否可信，并在保留双模态互补收益的同时抑制错误模态、错误融合或错误上下文路由？**

下一方法若成立，贡献应来自**可靠性判断和条件使用信息**，而不是简单再增加一个模块或更多参数。

## 下一设计的最低要求

- RGB 与 DSM **双向**退化/缺失都必须覆盖，不能只优化 RGB 缺失。
- 可靠性信号应来自部署时可获得的输入/特征/预测一致性，不把 GT 当推理输入。
- 必须有同权重或严格配对对照，区分“可靠性机制”与“容量增加”。
- 同时报告 clean 保护与退化收益，不能只提高坏输入而牺牲正常输入。
- 保留按类别、按区域、按退化强度的机制统计。
- 开发数据与最终测试严格隔离；当前不加载 Test6/held4/final。
- 先设门槛与停止条件，再训练；负结果不后验换门槛追正。

## 当前执行决定

- Post-T paired v2：**CLOSED / NOT_ACCEPTED_AS_SUCCESS**。
- Structured Failure Phase1A：**CLOSED / NO_SUPPORT_THIS_PROTOCOL**。
- 继续加 16k/更多步数：**不派发**。
- Structured 20→40 / Phase1B / Phase2：**不派发**。
- 新 seed / block 数扫描 / checkpoint 后验改选：**不派发**。
- Test6 / held4 / final：**保持关闭**。
- 下一实验：**DESIGN_REVIEW_NOT_REGISTERED**，没有后台队列、没有 GPU 任务。
