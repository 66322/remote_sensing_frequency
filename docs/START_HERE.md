# 共享入口：Phase2首次smoke失败，CE技术修复待用户执行（2026-10-13）

最后查询2026-10-13T15:02:06.544744+08:00原队列TECHNICAL_FAILURE_HOLD、所有进程退出；两卡同一CUDA NLL确定性算子错误，正式训练尚未开始。修复保留严格确定性与原mean CE目标，12项CPU检查通过，真实GPU待重新smoke；新技术替换队列尚未登记。

先读[研究决定](current/RESEARCH_DECISION.md)、[当前交接](current/HANDOFF.md)、[状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)、[技术修复门禁](protocols/PHASE_2_CE_TECHNICAL_FIX_20261013.md)、[执行协议](protocols/PHASE_2_EXECUTION_20261013.md)、[科学设计](protocols/PHASE_2_MATCHED_COMPLEMENTARITY_20261013.md)。旧目录保留，仅用户显式专项技术替换；不重复普通enqueue、不重启旧controller、不重跑其他配方或增seed。GPU0/1、无24h截止、无SSH/Test6/held4/final。主线及阶段证据边界保持。
