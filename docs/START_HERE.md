# 共享入口：Phase2.4已进入D1（2026-10-14）

最后观测：2026-10-14T20:09:38.622155+08:00；查询时间20:09:42.751022+08:00。用户回传status/日志，QUEUE=D1、控制器和GPU0/1均LIVE=True；这是该时刻观测，不是实时状态。

SMOKE=12；D1累计393/642，其中10个核心smoke复用，本阶段新完成383/632，剩249。CPU_PENDING=0，查询时无等待中的CPU case；两卡仍正在处理case。当前阶段估计剩0.29218小时（约17.5分钟，约20:27结束）；此估计仅覆盖D1，不覆盖后续分析和条件训练。

先读[研究决定](current/RESEARCH_DECISION.md)、[交接](current/HANDOFF.md)、[状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)，再读[最新观测](../records/phase24_registration_20261014/observation_200938.json)、[执行协议](protocols/PHASE_24_EXECUTION_20261014.md)、[科学门禁](protocols/PHASE_24_DIAGNOSIS_AND_CONDITIONAL_HEADS_20261014.md)。

保持原队列自动继续，后续只读查询，不重复登记或重启。研究主线RGB–DSM条件互补与退化/缺失分割不变，恢复旁支。原C/L和B1/B3门禁不改；T0 clean8k必做，T1/T2/T3按门禁，最多4小头32k，0新专家/训练seed。GPU0/1≥24h可续，无硬截止，无SSH/Test6/held4/final或自动失败重试。
