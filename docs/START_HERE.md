# 共享入口：Phase2执行包已实现（2026-10-13）

用户已授权按规划执行，READY_FOR_USER_LAUNCH / SERVER_GPU_SMOKE_REQUIRED，无新服务器登记。4核心训练48k，门禁通过后最多6训练64k，GPU0/1，无24h强停。

读取[研究决定](current/RESEARCH_DECISION.md)、[HANDOFF](current/HANDOFF.md)、[PROJECT_STATUS](current/PROJECT_STATUS.md)、[NEXT_EXPERIMENT](current/NEXT_EXPERIMENT.md)、[执行协议](protocols/PHASE_2_EXECUTION_20261013.md)、[科学设计](protocols/PHASE_2_MATCHED_COMPLEMENTARITY_20261013.md)、[技术验收](../records/phase2_implementation_20261013/verification.json)。9CPU检查通过，真实两卡batch16 smoke自动先行，失败HOLD不自动重试。

只读输入驻留、GPU共享cache、CPU随case流水、固定流hash与精确回退已实现；启动检查内存/CPU quota/各卡空闲与600GiB磁盘预留。所有产物在/home/jovyan/zzx对应独立records目录，无SSH/Test6/held4/final/extra seed。用户执行enqueue_phase2 bootstrap后才有真实目录/PID，不把本地CPU检查当GPU实验。[发现与旧结果](experiments/FINDINGS_REGISTRY_PHASE2_20261013.md)保持；旧入口已归档history/pre_phase2_execution_20261013。
