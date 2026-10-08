# 共享入口：Post-S1 GPU0执行包就绪，登记已回报，进度待查询

按[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)→[索引](experiments/rebuild_v1/INDEX.md)读取。GitHub同分支为共享权威。

最新服务器登记回报（用户终端，2026-10-08）：SUPPORT_QUEUE_REGISTERED，目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_s1_support_20261008T234921_1890161，controller PID1890742，GPU=0 ONLY，TRAINING_JOBS=10、NEW_STEPS=80000、Q_RESERVED_NOT_RUNNABLE=4；日志nohup_20261008T234938791083.log。目录23:49:21及日志23:49:38.791083为命名时间标记，不是queue observed_at。当前REGISTERED_PROGRESS_NOT_YET_QUERIED，尚无controller/worker存活、D0/D1进度、CUDA首步或完成回报，不能写为训练已确认。

原队列登记前检查回报：最后观测2026-10-08T06:37:48.607436+08:00，COMPLETE RELEASED。登记前CPU检查成功返回由执行入口链推断，服务器cpu_checks.log尚未单独接收；本地22项/12Python语法检查保持其合成CPU范围。

用户已授权实施[规划](protocols/POST_S1_SUPPORT_GPU0_PLAN_20261008.md)，[冻结执行协议](protocols/POST_S1_SUPPORT_EXECUTION_20261008.md)及GPU0独立执行包CPU22项/语法12Python文件通过，REGISTERED_PROGRESS_NOT_YET_QUERIED，真实GPU证据待收。D0/D1零训练诊断→10组8000步配对训练→E六压力条件→独立汇总；Q四组仅条件储备。约33—57h，首个完整作业后校准。

仅物理GPU0，physical_gpus=[0]、CUDA_VISIBLE_DEVICES=0、单worker FIFO，所有诊断/训练/推理/恢复均不得使用GPU1。nohup、全部记录/快照/cache/temporary/上传worktree在zzx对应新目录；用户终端执行，无SSH，无Test6/独立final/held4、追加seed或失败配方自动重跑。旧双卡入口不适用于本轮。

[前置N3/S1结果](experiments/POST_N3_S1_RESULTS_20261008.md)：N3增量不足；S1 RGB局部+4.102pp但退化保护失败，旧gate不改判。主线角色保持，新代码不等于成立贡献。新入口enqueue_post_s1_support.py先核前队列/锁/绑定、CPU检查、幂等登记并nohup；不要运行旧双卡enqueue或重复队列。
