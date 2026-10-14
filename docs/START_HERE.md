# 共享入口：Phase2.4下一阶段规划已登记（2026-10-14）

当前状态：**PLAN_ONLY_NOT_IMPLEMENTED_NOT_ENQUEUED**。用户本轮要求先规划；未实现新执行包，未查询实时服务器、未注册或启动新队列。GPU0/1资源窗口至少24小时，可继续；不是24小时硬截止。

依次读[研究决定](current/RESEARCH_DECISION.md)、[交接](current/HANDOFF.md)、[状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)，再读[Phase2.4诊断与条件小头完整规划](protocols/PHASE_24_DIAGNOSIS_AND_CONDITIONAL_HEADS_20261014.md)、[资源/方法审计](../records/phase24_planning_20261014/resource_and_method_audit.json)、[Phase2结果](experiments/PHASE_2_RESULTS_20261014.md)。

主线仍RGB–DSM条件互补与退化/缺失分割，恢复旁支。下一问题：识别DSM条件补救并保护强RGB。先复用旧计数、冻结专家联合诊断、cross-tile校准/部署探针，再按门禁决定小头配对；最多4个新小头32k更新，0新专家、0追加seed，此为计划上限而非已派任务。原B1/B3停止不改。

Phase2运行151120_1310582最后已验收完成记录2026-10-14T00:39:03.210695+08:00；核心4训练48k，上传dc335e0d。用户清理完成回执2026-10-14T12:13:25.974504+08:00：35910/35910文件，旧val/head cache及compact数组已退役，必要权重/原CM/代码/输入/L tail坐标保留。不重复启动旧队列或清理。

新实验默认有界RAM、最后消费者即回收，不整轮落盘8000步缓存或逐case整图预测；执行前必须实现并验收。[存储规则](protocols/EXPERIMENT_ARTIFACT_RETENTION_20261013.md)。服务器由用户执行，无SSH、自动失败重试、Test6/held4/final访问。旧入口归档[history](history/20261014_before_phase24_plan/START_HERE.md)。
