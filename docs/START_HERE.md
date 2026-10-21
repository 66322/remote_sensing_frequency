# 共享入口：后续研究问题与方法规划，M2-A尚未启动（2026-10-22）

先读[研究决定](current/RESEARCH_DECISION.md)、[交接](current/HANDOFF.md)、[当前状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)。本轮新增[研究选择与跨领域方法草案](experiments/POST_M2_RESEARCH_OPTIONS_20261022.md)，包括已有问题的新解法、最小对照、公开数据和去留条件；全部是建议，未成为新执行队列。

用户明确：M2尚未运行；时间不限、研究问题和创新性优先，公开数据可更换。已有研究不自动否决选题，应考虑更好的建模和方法迁移。当前主线角色仍为RGB–DSM条件互补与退化/缺失分割，恢复为旁支；候选换题未自动取代主线。

M2-A代码已实现，核心108×32k=345.6万更新。设计与科学门禁以[M2完整协议](protocols/PHASE3_M2_ERROR_CORRESPONDENCE_20261015.md)及[执行修订](protocols/PHASE3_M2_EXECUTION_20261016.md)为准。本地16项检查15通过、1项Linux FD待服务器，无M2 run/PID、实际fold或现场CUDA回执。

服务器由用户执行，只用GPU0/1；2026-10-16忙碌是历史报告，当前空闲未知。本轮未启动、重跑或修改M2队列；B90仍条件扩展，C81预算储备。M1幅度配方关闭。Val2/Test6/held4/final不进入M2，另一篇点云研究独立。RAM有界处理，结果交付按服务器自检＋报告/CSV/充分计数，不恢复整轮磁盘缓存或例行全包下载。
