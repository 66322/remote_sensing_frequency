# 共享入口：Post-S1 GPU0执行包就绪，服务器待登记

按[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)→[索引](experiments/rebuild_v1/INDEX.md)读取。GitHub同分支为共享权威。

最后服务器查询仍为2026-10-08T22:11:10.555448+08:00；原queue最后观测06:37:48.607436，N3_S1_COMPLETE_AWAITING_REVIEW，九组COMPLETE/8000，查询时controller/worker LIVE=False。本次没有新的服务器登记、PID或GPU进度回报。

用户已授权实施[规划](protocols/POST_S1_SUPPORT_GPU0_PLAN_20261008.md)，[冻结执行协议](protocols/POST_S1_SUPPORT_EXECUTION_20261008.md)及GPU0独立执行包CPU22项/语法12Python文件通过，READY_NOT_REGISTERED，真实GPU证据待收。D0/D1零训练诊断→10组8000步配对训练→E六压力条件→独立汇总；Q四组仅条件储备。约33—57h，首个完整作业后校准。

仅物理GPU0，physical_gpus=[0]、CUDA_VISIBLE_DEVICES=0、单worker FIFO，所有诊断/训练/推理/恢复均不得使用GPU1。nohup、全部记录/快照/cache/temporary/上传worktree在zzx对应新目录；用户终端执行，无SSH，无Test6/独立final/held4、追加seed或失败配方自动重跑。旧双卡入口不适用于本轮。

[前置N3/S1结果](experiments/POST_N3_S1_RESULTS_20261008.md)：N3增量不足；S1 RGB局部+4.102pp但退化保护失败，旧gate不改判。主线角色保持，新代码不等于成立贡献。新入口enqueue_post_s1_support.py先核前队列/锁/绑定、CPU检查、幂等登记并nohup；不要运行旧双卡enqueue或重复队列。
