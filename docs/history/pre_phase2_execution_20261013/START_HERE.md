# 共享入口：Phase2匹配互补设计（2026-10-13）

当前DESIGN_SPECIFIED / EXECUTION_NOT_IMPLEMENTED_NOT_REGISTERED。用户要求GPU0/1、一天以上可用窗口、内存驻留与并行分析；核心4训练48k，条件性最多6训练64k。旧Phase1.5完整完成并已核验，当前没有新队列。

先读[研究决定](current/RESEARCH_DECISION.md)、[HANDOFF](current/HANDOFF.md)、[PROJECT_STATUS](current/PROJECT_STATUS.md)、[NEXT_EXPERIMENT](current/NEXT_EXPERIMENT.md)、[Phase2完整设计](protocols/PHASE_2_MATCHED_COMPLEMENTARITY_20261013.md)、[发现登记](experiments/FINDINGS_REGISTRY_PHASE2_20261013.md)和[实验索引](experiments/rebuild_v1/INDEX.md)。

[Phase1.5完整结果](experiments/PHASE_1_5_RESULTS_20261013.md)保持；新补充：720个旧S1案例已记录内部DSM logits精确回退，身份检验无需重复推理。下一轮必须区分已知missing硬回退与未报告corruption的可观测可靠性选择，先静态后动态，不由oracle直接派发。

最后服务器查询仍2026-10-13T11:35:58.181880+08:00，原队列完成观测11:31:16.761032；本次没有实时服务器访问。无SSH、Test6/held4/final、新训练seed或失败配方自动重跑。旧草案由本次设计替代、旧入口归档history/pre_phase2_design_20261013；[记录来源规则](protocols/RECORD_SOURCE_AND_HANDOFF.md)继续适用。