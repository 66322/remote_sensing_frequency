# 当前交接：Post-S1执行包就绪，GPU0已登记，CPU准备已确认

最后服务器只读查询（用户终端）：QUERY_OBSERVED=2026-10-08T23:53:14.323317+08:00，queue LAST_OBSERVED=2026-10-08T23:49:50.130388+08:00，PREPARING_D0_MASKS，controller PID1890742 LIVE=True；CPU=RUNNING。CPU_PROGRESS在23:51:48.651736报告D0 / 3_11 / rgb_U。D1、P6/P7/P8/P9/P4/P5/P2/P3/P0/P1、E十二项全部PENDING、PID−1、LIVE=False，无CUDA首步或科学结果。Q=RESERVED_NOT_AUTOMATIC。当前显卡空闲符合CPU准备阶段，未见本次错误回报；不能据此宣布D0完成或训练已开始。

既有登记保持：执行2c5e7d6f383cfe454415d4e106179930264f1141，目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_s1_support_20261008T234921_1890161，nohup_20261008T234938791083.log，GPU0 ONLY，10训练/80000新步；Q四组不可运行储备。登记前CPU检查成功返回由入口执行链推断，服务器检查日志未单收。

原队列登记前检查回报：最后观测2026-10-08T06:37:48.607436+08:00，COMPLETE RELEASED。登记前CPU检查成功返回由执行入口链推断，服务器cpu_checks.log尚未单独接收；本地22项/12Python语法检查保持其合成CPU范围。

用户已授权按GPU0[规划](../protocols/POST_S1_SUPPORT_GPU0_PLAN_20261008.md)实施。[冻结执行包](../protocols/POST_S1_SUPPORT_EXECUTION_20261008.md)已实现，PREPARING_D0_MASKS：D0复用/拼接→D1四权重四策略→P十组→E六条件→独立汇总。P7固定候选、S1-0基座SHA、新8000×10/seed42、fixed8000主比较、原科学门槛保持。CPU合成检查22项及12Python语法通过；没有真实服务器权重/backbone/GPU复跑，登记前同包CPU检查已成功返回（执行链推断，原log待收）。

可行性探索，主线仍RGB–DSM条件互补与退化/缺失分割，任务恢复旁支。N3当前区域增量不足，S1 RGB局部+4.102047pp但aux_shift8/3_11−0.391546pp保护失败，旧gate维持False；本轮研究缺失支持与参数隔离，不自动升级单向收益为双向贡献。N5/N2/C旧去留保持，R1/N4/R2不激活。

仅物理GPU0，physical_gpus=[0]、CUDA_VISIBLE_DEVICES=0、单worker FIFO，所有诊断/训练/推理/恢复均不得使用GPU1。nohup、全部记录/快照/cache/temporary/上传worktree在zzx对应新目录；用户终端执行，无SSH，无Test6/独立final/held4、追加seed或失败配方自动重跑。旧双卡入口不适用于本轮。

下一步只读已有目录code/scripts/status_post_s1_support.py、nohup_20261008T234938791083.log及可选preparation.log，继续获取queue最后观测/存活/阶段/worker首步。不要再次enqueue、重启原N3/S1或创建第二条队列；完成/失败后显式upload_post_s1_support_records.py，轻量原件回读复算后评科学去留。CPU准备阶段GPU空闲不能直接判故障。

首轮预算约33—57h，首个冻结/共享完整作业后校准，无科学总时限。Q最多四组镜像DSM仅条件储备：D1同S1-0权重DSM信号与P7/U/E均过才标记资格，还需冻结具体DSM协议，不自动训练。

决定来源：用户明确“按上述规划进行”，授权执行包开发和终端启动安排。未采纳重跑N3/S1旧配方、改保护线、换后验候选、加seed或用GPU1。下一不确定性：收益是否来自可对齐上下文，参数隔离能否保护非缺失与DSM退化场景；P7失败保持固定去留，不扫超参挽救。[上一交接归档](../history/HANDOFF_PRE_POST_S1_SUPPORT_D0_20261008.md)。
