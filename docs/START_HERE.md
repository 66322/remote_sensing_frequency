# 共享入口：Phase 1.5 双卡诊断规划，待实现与smoke
权威分支：66322/remote_sensing_frequency / rebuild-v1-protocol-20260915。2026-10-12用户要求结合审查与论文规划至少一天，GPU0/1并行、超过一天继续，暂不处理单卡释放。

两轮旧实验已上传并验收：Post-T最后上传观测2026-10-12T11:03:22.917566+08:00，8/8 COMPLETE、PAIRED_SCREEN=False；Structured最后上传观测2026-10-12T16:32:44.762198+08:00，42/42 COMPLETE、NO_SUPPORT_THIS_PROTOCOL。这些是历史上传快照，未查询当前服务器实时进程。

当前新阶段为 **PHASE_1_5_V1_1_PLANNED_AWAITING_IMPLEMENTATION_AND_SMOKE**。已有具体矩阵、24–48h资源窗口和去留树；没有本阶段服务器登记/进度证据，不把规划说成已开跑。全量推理清单按缓存估约1538次新完整tile推理（含最多160次熵补全），0新训练，smoke全PASS再登记。

研究主线RGB–DSM双向条件互补与退化/缺失；下一步先分解RGB局部缺失可恢复性，可靠性/routing和残差context均是条件候选。不得从旧current中的“直接优先routing”跳过诊断。

R16−H16=+0.348562pp，两tile正，局部门槛通过；总失败来自5/6 E条件相对R0底线。独立8k/16k预算未支持盲目续训，但R16自身8k→16k仍+0.618217pp，不宣称后半程不学习。S1主PE=+0.122522pp、CI跨0，RGB-only PE=+3.119077pp；S1约21pp为缺失区伤害。跨模型差不单独证明DSM因果补偿；R16固定模型特征内容干预提供更直接线索。

先读：[新交接](current/NEW_CHAT_HANDOFF_20261011.md)→[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一实验](current/NEXT_EXPERIMENT.md)→[索引](experiments/rebuild_v1/INDEX.md)→[双卡规划](protocols/PHASE_1_5_TWO_GPU_PLAN_20261012.md)及所引原件。

Test6/held4/final保持关闭；不扩seed/mask或重跑失败配方。服务器由用户执行，无SSH，产物/home/jovyan/zzx；前版入口归档docs/history/pre_phase15_two_gpu_20261012/。
