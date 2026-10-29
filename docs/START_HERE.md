# 共享入口：M2结果已收尾，正在整理证据与清理存储（2026-10-29）

先读[研究决定](current/RESEARCH_DECISION.md)、[当前交接](current/HANDOFF.md)、[状态](current/PROJECT_STATUS.md)、[唯一下一步](current/NEXT_EXPERIMENT.md)。长期规则为[AGENTS](../AGENTS.md)、[执行约定](protocols/EXECUTION_CONTRACT.md)与[稳定接续入口](current/NEW_CHAT_HANDOFF.md)。

最后服务器观测2026-10-29 10:29:51+08:00。M2于08:43完整完成108项训练、77,868例评价；G0/H2/G3通过，G1/G2/G4未通过，当前DF错误对应性配方不再扩展。不是所有RGB–DSM问题失败。[结论与主表](experiments/PHASE3_M2_ACCEPTANCE_AND_CLOSEOUT_20261029.md)、[轻量终端证据](../records/phase3_m2_closeout_terminal_20261029/)。

旧队列在M2 G0通过后自动进入J，J2因CUDA交叉熵确定性兼容错误停止；不影响M2。10:29两GPU空闲，J无科学结论、R/T/V未顺序派发。本轮没有修复或重启。

用户已授权整理上传证据、统计本次实验数据并清理无用权重/中间大文件。工具与[清理保留协议](protocols/PHASE3_M2_STORAGE_CLEANUP_20261029.md)已交付，尚无现场清理回执：保留18个R/D0端点和全部计数/配置/日志/原始数据/预训练，候选最多90个无后续用途端点及具名临时文件。用户要求上传后回读即可，不重复哈希；工具复用已有验收。

当前唯一下一步是用户执行固定发布版本统计/导出/清理，回传cleanup_result及轻量包位置/大小；收到后记录实际释放空间并补齐服务器轻量原件。没有服务器直连，不能从代码发布推断已经删除。原始M2权重全量保留的默认策略已由本轮明确授权修订，新retention单独记录，不改原验收事实。

研究角色不自动改变；[地图维护候选](experiments/INDEPENDENT_RESEARCH_ROUTE_20261023.md)与[分批方案](experiments/NEXT_STAGE_DECISION_EXPERIMENTS_20261027.md)仍待验证。规划先主比较、再扩评价，探索默认单seed，必要重复通常先两个。封存split不开放，旧bootstrap不再执行。

[前一版共享入口](history/START_HERE_20261029_BEFORE_M2_CLOSEOUT.md)仅为历史。
