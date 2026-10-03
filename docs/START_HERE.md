# 共享入口：18＋4机制队列已启动，最后观测等待D30

权威仓库66322/remote_sensing_frequency，分支rebuild-v1-protocol-20260915。先读[研究决定](current/RESEARCH_DECISION.md)→[交接](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)，再核对原始记录和源码；本地只作工作副本。

主问题仍为RGB外观/语义与DSM高度/几何的双向条件互补及任一模态退化/缺失下的可靠分割。处于论文可行性探索，频率、语义可靠性、专家与共享/私有只是候选解法；任务驱动SR/恢复仍为旁支，没有自动转向或确认性贡献。

D30四项结果支持“当前恢复项引入明显信息取舍”，不能归因整个DSM无用；P仅+0.041pp、R−2.013pp，交互项+0.177pp，不是负交互。原始逐tile重算和最后两项结果待收齐。[分析](experiments/D30_FOUR_ARM_REVIEW_20261003.md)。

用户授权执行原12＋4规划并增加组数，已实现A6＋B6＋C6主体和B3通过才运行的F4。固定候选/门槛不由敏感性最佳结果替代，不重新开放旧失败配方或D29。[协议](protocols/POST_D30_EXECUTION_20261003.md)。

最后用户回传为2026-10-04 00:08启动日志（时间取目录名，日志行无独立时间戳）：Post-D30控制器PID2450552已由nohup启动，CPU检查通过，记录`PORTFOLIO_WAITING_D30 RUNNING`，即已排队等待D30。执行commit固定01ec8dee82f7e272f6a650aaf9f3e619a0e7c516，新目录`research_post_d30_mechanisms_20261004T000812_2446364`；所给日志尚无新GPU worker启动。没有/proc直接存活检查或完整queue_status回传，不能把此次日志当作持续实时存活保证。D30在该日志中被间接观测为RUNNING；其最后直接进度仍为10月3日23:17，随后四项完成指标已分析，PR_area/PR_pixel、重放效果及原矩阵待收。

只使用物理GPU0/1，两张H10080GB；RAM/磁盘充足，无资源探针。seed42、8000步、batch16无累积、nohup。快照、临时、缓存、日志全部在/home/jovyan/zzx对应实验目录。用户在服务器终端执行，无SSH；Test6与独立final禁读。重复开发Val2不是确认性泛化证据。GitHub本分支为共享权威，大预测/checkpoint本体留服务器并索引。

旧入口全文已[归档](history/pre_post_D30_execution_20261003/START_HERE.md)。

[本次启动观测](../records/research_post_d30_mechanisms_20261004T000812_2446364/launch_observation_20261004T000812.json)。
