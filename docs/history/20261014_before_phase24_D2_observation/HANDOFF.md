# 当前交接：Phase2.4 D1运行观测（2026-10-14）

最后观测：2026-10-14T20:19:30.960798+08:00；查询时间20:19:32.558327+08:00。用户回传status/日志，QUEUE=D1、控制器和GPU0/1均LIVE=True；这是该时刻观测，不是实时状态。

运行目录 /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase24_protected_20261014T193915_2149100；执行5a84f0eacabe5d6f1c7ed1638e6a9291c58e151f，控制器2149894，GPU0/1进程2149964/2149965，日志nohup_20261014T193920570637.log。

SMOKE=12；D1累计534/642，其中10个核心smoke复用，本阶段新完成524/632，剩108。CPU_PENDING=0，查询时无等待中的CPU case；两卡仍正在处理case。当前阶段估计剩0.12654小时（约7.6分钟，约20:27结束）；此估计仅覆盖D1，不覆盖后续分析和条件训练。

D1进入意味着固定控制器的输入、双卡smoke和CM桥接门禁已通过；输入48/48完成。尚未独立接收smoke_pass等原始JSON逐字节验收，不能据控制台状态声称正式机制结论或训练结果。

同一匿名RAM case的CPU16/24/32进程基准分别5.7172/4.9965/4.9580秒，三者结果SHA完全一致，选择32进程，每个数值库1线程；不是全局单线程。两卡峰值allocated约5.54GiB，各包2.304GB是匿名RAM通信，非逐case磁盘产物。xFormers disabled/not available符合固定配置，本次日志未显示异常。

研究主线RGB–DSM条件互补与退化/缺失分割不变，恢复旁支。原C/L和B1/B3门禁不改；T0 clean8k必做，T1/T2/T3按门禁，最多4小头32k，0新专家/训练seed。GPU0/1≥24h可续，无硬截止，无SSH/Test6/held4/final或自动失败重试。

原185408_2127460零更新IPC失败快照保留，不再用于进度；本次正常D1不需修复或再次启动。下一动作只读status查询，D1后等待source-only拟合、固定端点评价和T0/条件头的实际门禁。完成后用户显式upload_phase24.py，白名单轻量归档回读。旧Phase2大cache已退役，不恢复。

[最新观测](../../records/phase24_registration_20261014/observation_201930.json)；[执行](../protocols/PHASE_24_EXECUTION_20261014.md)；[此前交接](../history/20261014_before_phase24_D1_observation/HANDOFF.md)。

[新对话完整接续说明](NEW_CHAT_HANDOFF_20261014.md)：执行快照、门禁、资源回收、原件验收及避免重复派发。
