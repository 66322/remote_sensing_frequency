# 共享入口：M2-A核心执行包已实现，尚未在服务器启动（2026-10-16）

先读[当前状态](current/PROJECT_STATUS.md)、[交接](current/HANDOFF.md)、[下一步](current/NEXT_EXPERIMENT.md)、[研究决定](current/RESEARCH_DECISION.md)，再读[M2完整协议](protocols/PHASE3_M2_ERROR_CORRESPONDENCE_20261015.md)及[本轮具体执行修订](protocols/PHASE3_M2_EXECUTION_20261016.md)。

用户授权按M2实现具体实验、修正问题、加速统计并精简结果交付。核心108×32k=345.6万更新不变。DMix尺度匹配、DF对DClean的融合比较、damaged证据和明确保护范围已落实。CPU最多32个fork进程，与双卡训练/推理流水并行；每次只保留一个tile的有限预测，不缓存整轮磁盘logits。

本地15项检查14通过，Linux真实跨进程FD检查待服务器。无M2 run/PID、现场GPU或真实fold回执，不能声称已启动。服务器由用户执行；仅GPU0/1，旧快照有vLLM占用，必须重新确认，绝不清理外来进程。

结果在服务器自检后上传报告、汇总表和三个fold充分计数，不例行下载重验整包。B90仍待A门禁与反向执行冻结；C81为预算储备，总279上限不变。M1幅度配方关闭，Val2/Test6/held4/final与另一篇点云均不进入本轮。
