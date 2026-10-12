# 当前状态（2026-10-12）

两轮旧实验已上传并验收：Post-T最后上传观测2026-10-12T11:03:22.917566+08:00，8/8 COMPLETE、PAIRED_SCREEN=False；Structured最后上传观测2026-10-12T16:32:44.762198+08:00，42/42 COMPLETE、NO_SUPPORT_THIS_PROTOCOL。这些是历史上传快照，未查询当前服务器实时进程。

新阶段状态：**PHASE_1_5_V1_1_PLANNED_AWAITING_IMPLEMENTATION_AND_SMOKE**。

已完成：最新结果/旧路由失败/审查意见/原始文献核对，Phase1.5执行前澄清、科学矩阵、双卡时间账本与后继决策树。
未完成：新Phase1.5执行代码与known-answer、服务器真实smoke、登记、运行和科学验收。没有新PID或新完成结果。

R16−H16=+0.348562pp，两tile正，局部门槛通过；总失败来自5/6 E条件相对R0底线。独立8k/16k预算未支持盲目续训，但R16自身8k→16k仍+0.618217pp，不宣称后半程不学习。S1主PE=+0.122522pp、CI跨0，RGB-only PE=+3.119077pp；S1约21pp为缺失区伤害。跨模型差不单独证明DSM因果补偿；R16固定模型特征内容干预提供更直接线索。

## 资源与数量
GPU0/1同时工作，0新训练/0优化器更新，5项诊断。完整核心新增推理1378，S1熵缓存补全最多160，按1538预算；已有缓存合法命中可省。旧缓存缺口在实际manifest说明，不新增mask样本。24–48h是预留窗口而非保证ETA，24h未完继续；提前完成不填时长。

下一步实现独立评估包、smoke id=1/tile3_11，全部通过后登记；核查原队列/锁防重复。旧负科学gate不变，Test6/held4/final关闭，服务器仅用户终端执行。

[双卡具体规划](../protocols/PHASE_1_5_TWO_GPU_PLAN_20261012.md)、[Phase1.5主协议v1.1](../protocols/PHASE_1_5_RECOVERABILITY_20261012.md)、[文献映射](../literature/PHASE_1_5_METHOD_CANDIDATES_20261012.md)、[关键原件复核](../experiments/LATEST_RESULTS_KEY_REVIEW_20261012.md)。
