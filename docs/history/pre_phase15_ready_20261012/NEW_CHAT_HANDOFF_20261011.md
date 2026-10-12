# 新对话入口：Phase1.5双卡规划（更新2026-10-12）

两轮旧实验已上传并验收：Post-T最后上传观测2026-10-12T11:03:22.917566+08:00，8/8 COMPLETE、PAIRED_SCREEN=False；Structured最后上传观测2026-10-12T16:32:44.762198+08:00，42/42 COMPLETE、NO_SUPPORT_THIS_PROTOCOL。这些是历史上传快照，未查询当前服务器实时进程。

最新是**PHASE_1_5_V1_1_PLANNED_AWAITING_IMPLEMENTATION_AND_SMOKE**，不再沿用“直接训练reliability”或“下一协议尚未设计”的旧入口。具体执行包仍未实现/登记。

用户最新授权：GPU0＋GPU1，预留一天以上，跑不完继续；本轮不用考虑释放单卡。按1538左右完整tile推理的账本预留24–48h，0训练/0新seed；真实ETA待smoke，不承诺两小时。

先读[研究决定](RESEARCH_DECISION.md)、[HANDOFF](HANDOFF.md)、[状态](PROJECT_STATUS.md)、[下一实验](NEXT_EXPERIMENT.md)，再读双卡规划及v1.1主协议。现有科学负gate不改，后继训练只作条件设计。

R16−H16=+0.348562pp，两tile正，局部门槛通过；总失败来自5/6 E条件相对R0底线。独立8k/16k预算未支持盲目续训，但R16自身8k→16k仍+0.618217pp，不宣称后半程不学习。S1主PE=+0.122522pp、CI跨0，RGB-only PE=+3.119077pp；S1约21pp为缺失区伤害。跨模型差不单独证明DSM因果补偿；R16固定模型特征内容干预提供更直接线索。

[双卡具体规划](../protocols/PHASE_1_5_TWO_GPU_PLAN_20261012.md)、[Phase1.5主协议v1.1](../protocols/PHASE_1_5_RECOVERABILITY_20261012.md)、[文献映射](../literature/PHASE_1_5_METHOD_CANDIDATES_20261012.md)、[关键原件复核](../experiments/LATEST_RESULTS_KEY_REVIEW_20261012.md)。
