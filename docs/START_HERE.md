# 共享入口：Phase2.4执行包已完成，等待服务器smoke（2026-10-14）

当前状态：**IMPLEMENTED_CPU_CHECKED_AWAITING_SERVER_SMOKE**。用户已要求按规划具体安排；代码和CPU检查完成，尚无新运行ID或实时服务器观测。下一动作是用户执行固定提交SHA的登记入口；入口先查已有队列，拒绝重复登记。

先读[研究决定](current/RESEARCH_DECISION.md)、[交接](current/HANDOFF.md)、[状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)，再读[执行协议](protocols/PHASE_24_EXECUTION_20261014.md)、[科学门禁规划](protocols/PHASE_24_DIAGNOSIS_AND_CONDITIONAL_HEADS_20261014.md)、[实现检查](../records/phase24_execution_20261014/implementation_audit.json)、[Phase2结果](experiments/PHASE_2_RESULTS_20261014.md)。

主线仍RGB–DSM条件互补与退化/缺失分割，恢复旁支。D0–D3先诊断，T0 clean分布控制必做，T1/T2/T3按保护门禁进入；最多4小头32k，0新专家/追加训练seed，原B1/B3停止不变。

GPU0/1、至少24h资源预约、未完成继续，无硬截止；本地18项检查通过、2项Linux检查待服务器，不能代替真实CUDA验收。原9.8GB规范化输入只读共享RAM，匿名memfd/并行stripe处理，临时产物用完释放；不恢复旧大缓存。服务器由用户执行，无SSH、Test6/held4/final或自动失败重试。

Phase2最后已验收完成2026-10-14T00:39:03.210695+08:00，上传dc335e0d；清理回执12:13:25.974504+08:00，35910/35910完成，不重复旧队列/清理。[原规划状态入口](history/20261014_before_phase24_execution/START_HERE.md)。
