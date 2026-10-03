# 共享入口：D30部分结果已分析，18＋4后接机制实验已实现

权威仓库66322/remote_sensing_frequency，分支rebuild-v1-protocol-20260915。先读[研究决定](current/RESEARCH_DECISION.md)→[交接](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)，再核对原始记录和源码；本地只作工作副本。

主问题仍为RGB外观/语义与DSM高度/几何的双向条件互补及任一模态退化/缺失下的可靠分割。处于论文可行性探索，频率、语义可靠性、专家与共享/私有只是候选解法；任务驱动SR/恢复仍为旁支，没有自动转向或确认性贡献。

D30四项结果支持“当前恢复项引入明显信息取舍”，不能归因整个DSM无用；P仅+0.041pp、R−2.013pp，交互项+0.177pp，不是负交互。原始逐tile重算和最后两项结果待收齐。[分析](experiments/D30_FOUR_ARM_REVIEW_20261003.md)。

用户授权执行原12＋4规划并增加组数，已实现A6＋B6＋C6主体和B3通过才运行的F4。固定候选/门槛不由敏感性最佳结果替代，不重新开放旧失败配方或D29。[协议](protocols/POST_D30_EXECUTION_20261003.md)。

D30最新直接运行观测仍为2026-10-03T23:17:45.146029+08:00，控制器2349619存活，PR_area2860/8000、PR_pixel2420/8000；这不是实时状态。随后用户回传S0/S1/P/R的selected及fixed8000完成指标，未包含PR_area/PR_pixel、重放效果或原矩阵。新18＋4队列已实现并通过10项CPU检查，**尚无服务器启动、排队或存活观测**；必须执行下一步里的nohup指令后才可称排队。

只使用物理GPU0/1，两张H10080GB；RAM/磁盘充足，无资源探针。seed42、8000步、batch16无累积、nohup。快照、临时、缓存、日志全部在/home/jovyan/zzx对应实验目录。用户在服务器终端执行，无SSH；Test6与独立final禁读。重复开发Val2不是确认性泛化证据。GitHub本分支为共享权威，大预测/checkpoint本体留服务器并索引。

旧入口全文已[归档](history/pre_post_D30_execution_20261003/START_HERE.md)。
