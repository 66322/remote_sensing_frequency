# 共享入口：Phase3-M1执行包就绪；服务器尚未报告启动（2026-10-15）

用户要求按设计落实新实验、GPU0/1避免空等待、临时产物用完清理。双卡调度、训练/推理/统计、紧凑归档和生命周期已实现；16个本机适用检查通过，Linux传递及真实GPU检查由目标平台定向执行。目前没有新服务器运行回执或结果。

先读[下一步](current/NEXT_EXPERIMENT.md)、[交接](current/HANDOFF.md)、[执行与清理协议](protocols/PHASE3_M1_EXECUTION_20261015.md)、[科学设计](protocols/PHASE3_M1_DESIGN_20261015.md)。启动固定提交bootstrap，不用完整克隆大归档仓库，不再恢复旧队列。

Phase3-M1仅本篇RGB/DSM/标签；Fit12/Val2、两个DSM种子、11新主训练，最多2条件反证，固定16k。临时RAM按最后消费者退役，成功恢复状态与运行缓存自动清理，保留必要权重和全部科学证据。点云属于另一篇论文；Test6/held4/final封闭。

原Phase2.4原件已验收，calibrated/probe=False，T0完成8k，T1/T2/T3未派发。详见[正式验收](experiments/PHASE_24_ACCEPTANCE_AND_ROUTE_REVIEW_20261015.md)。新执行包就绪不代表新科学主张已成立。
