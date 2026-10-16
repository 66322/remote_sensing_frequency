# 共享入口（最后观测2026-10-13 19:36）

Phase2当前目录151120_1310582在19:36查询为EVALUATING_B0_16000，两卡评估worker存活；4项核心训练任务显示COMPLETE，科学结果待核验。records约2.69TiB，其中Phase2约578.2GiB，挂载盘可用3.0T。第一批旧预测删除31956完成，第二批脚本就绪但尚未执行。

先读[研究决定](current/RESEARCH_DECISION.md)、[交接](current/HANDOFF.md)、[状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)和[第二批清理协议](protocols/HISTORICAL_PREDICTION_SECOND_CLEANUP_20261013.md)。研究主线与Phase2门禁保持，无新队列、自动重试或Test6访问。服务器由用户操作，无SSH。下方为此前入口说明。

# 共享入口：Phase2配对专家训练已启动（最后观测2026-10-13 15:17:32）

新目录151120_1310582，prepare/双卡smoke/legacy_counts COMPLETE，A_RGB GPU0 step2180、A_DSM GPU1 step1740，controller/两训练worker存活。无正式验证结果，status里的ETA仅纯训练步数。容量600GiB是启动下限；源码估算核心750–850GiB、完整条件6训练约1TiB，等待实际df确认。缓存不自动删。详见HANDOFF最新观测，以下15:11等待描述为历史。

用户15:11启动回执确认新目录research_phase2_matched_20261013T151120_1310582、controller PID1310878、执行代码e5641e073bf4421e346f589199c291a6e94db8b2、GPU0/1。这是启动回执，不是实时status；准备、真实GPU CE/smoke和正式训练状态尚待新目录查询。原145903失败目录保留；勿重复enqueue或专项替换。

先读[研究决定](current/RESEARCH_DECISION.md)、[当前交接](current/HANDOFF.md)、[状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)、[技术修复门禁](protocols/PHASE_2_CE_TECHNICAL_FIX_20261013.md)、[执行协议](protocols/PHASE_2_EXECUTION_20261013.md)、[科学设计](protocols/PHASE_2_MATCHED_COMPLEMENTARITY_20261013.md)。12项CPU检查通过不替代真实GPU验证。核心4训练48k，门禁通过最多6训练64k，无24h截止，无SSH/Test6/held4/final或额外seed。[登记回执](../records/phase2_ce_fix_20261013/replacement_registration.txt)。
