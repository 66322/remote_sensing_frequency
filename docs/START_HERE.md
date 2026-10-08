# 共享入口：Post-S1 GPU0执行包就绪，登记已回报，CPU准备已确认

按[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)→[索引](experiments/rebuild_v1/INDEX.md)读取。GitHub同分支为共享权威。

最后服务器只读查询（用户终端）：QUERY_OBSERVED=2026-10-08T23:53:14.323317+08:00，queue LAST_OBSERVED=2026-10-08T23:49:50.130388+08:00，PREPARING_D0_MASKS，controller PID1890742 LIVE=True；CPU=RUNNING。CPU_PROGRESS在23:51:48.651736报告D0 / 3_11 / rgb_U。D1、P6/P7/P8/P9/P4/P5/P2/P3/P0/P1、E十二项全部PENDING、PID−1、LIVE=False，无CUDA首步或科学结果。Q=RESERVED_NOT_AUTOMATIC。当前显卡空闲符合CPU准备阶段，未见本次错误回报；不能据此宣布D0完成或训练已开始。

既有登记保持：执行2c5e7d6f383cfe454415d4e106179930264f1141，目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_s1_support_20261008T234921_1890161，nohup_20261008T234938791083.log，GPU0 ONLY，10训练/80000新步；Q四组不可运行储备。登记前CPU检查成功返回由入口执行链推断，服务器检查日志未单收。

原队列登记前检查回报：最后观测2026-10-08T06:37:48.607436+08:00，COMPLETE RELEASED。登记前CPU检查成功返回由执行入口链推断，服务器cpu_checks.log尚未单独接收；本地22项/12Python语法检查保持其合成CPU范围。

用户已授权实施[规划](protocols/POST_S1_SUPPORT_GPU0_PLAN_20261008.md)，[冻结执行协议](protocols/POST_S1_SUPPORT_EXECUTION_20261008.md)及GPU0独立执行包CPU22项/语法12Python文件通过，PREPARING_D0_MASKS，真实GPU证据待收。D0/D1零训练诊断→10组8000步配对训练→E六压力条件→独立汇总；Q四组仅条件储备。约33—57h，首个完整作业后校准。

仅物理GPU0，physical_gpus=[0]、CUDA_VISIBLE_DEVICES=0、单worker FIFO，所有诊断/训练/推理/恢复均不得使用GPU1。nohup、全部记录/快照/cache/temporary/上传worktree在zzx对应新目录；用户终端执行，无SSH，无Test6/独立final/held4、追加seed或失败配方自动重跑。旧双卡入口不适用于本轮。

[前置N3/S1结果](experiments/POST_N3_S1_RESULTS_20261008.md)：N3增量不足；S1 RGB局部+4.102pp但退化保护失败，旧gate不改判。主线角色保持，新代码不等于成立贡献。新入口enqueue_post_s1_support.py先核前队列/锁/绑定、CPU检查、幂等登记并nohup；不要运行旧双卡enqueue或重复队列。
