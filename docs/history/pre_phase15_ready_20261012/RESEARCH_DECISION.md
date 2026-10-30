# 当前研究决定：先做可恢复性分解（2026-10-12）

两轮旧实验已上传并验收：Post-T最后上传观测2026-10-12T11:03:22.917566+08:00，8/8 COMPLETE、PAIRED_SCREEN=False；Structured最后上传观测2026-10-12T16:32:44.762198+08:00，42/42 COMPLETE、NO_SUPPORT_THIS_PROTOCOL。这些是历史上传快照，未查询当前服务器实时进程。

R16−H16=+0.348562pp，两tile正，局部门槛通过；总失败来自5/6 E条件相对R0底线。独立8k/16k预算未支持盲目续训，但R16自身8k→16k仍+0.618217pp，不宣称后半程不学习。S1主PE=+0.122522pp、CI跨0，RGB-only PE=+3.119077pp；S1约21pp为缺失区伤害。跨模型差不单独证明DSM因果补偿；R16固定模型特征内容干预提供更直接线索。

## 研究角色与决定来源
主线仍是RGB–DSM双向条件互补与退化/缺失分割；任务驱动恢复旁支。已存在Phase1.5冻结协议，本次用户提交其审查意见并要求结合论文安排GPU0/1、至少一天且未完继续；随后取消本轮对单卡释放的关注。助手据此提出执行前v1.1澄清、约1538次完整tile推理的双卡24–48h资源规划。资源授权不是对新方法有效性的认可。

唯一下一科学问题是RGB局部缺失的可恢复性分解。Phase1.5全程零训练，A DSM对应干预、B nested剂量、C类别、D专家互补与可观测信号、E距离profile。旧Structured位置脆弱性gate不重开。

可靠性/routing从“下一默认方法”改为条件候选，理由：D27/D30旧失败未被新总负gate消除，现有oracle/可识别性证据仍不足。残差context也需诊断，不凭名称或小oracle自动入场。此为明确研究顺序/候选角色修订，不改主线或历史结论。

## 决策边界
raw五expert完整NB headroom的2/6pp保留为资源分流阈值，不是统计定理；高oracle还需部署可得信号下跨tile的专家偏好和超过最佳单专家的空间。旧DSM-only legacy限制与不完整池必须明示。GT class/真实mask解释不是可部署可学习性证明。

不采纳无证据的<2 GPU小时、单realization估方差、zero-init训练后恒等保护及“必然可发表”；完整分歧与修正写入双卡规划。未来四组残差或四组router只为条件设计储备，未登记、未实现，不自动训练。

[双卡具体规划](../protocols/PHASE_1_5_TWO_GPU_PLAN_20261012.md)、[Phase1.5主协议v1.1](../protocols/PHASE_1_5_RECOVERABILITY_20261012.md)、[文献映射](../literature/PHASE_1_5_METHOD_CANDIDATES_20261012.md)、[关键原件复核](../experiments/LATEST_RESULTS_KEY_REVIEW_20261012.md)。
