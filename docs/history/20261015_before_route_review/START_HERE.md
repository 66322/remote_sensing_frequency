# 共享入口：Phase2.4D1完成，D2与T0并行（2026-10-14）

最后观测：2026-10-14T20:28:16.847139+08:00；查询时间20:28:17.018087+08:00。用户回传status及60行日志尾部，QUEUE=D2、控制器和GPU0/1均LIVE=True；这是该时刻观测，不是实时状态。

SMOKE=12；D1累计642/642完成（复用10个核心smoke，本阶段新完成632/632）。D2已完成8/642，CPU_PENDING=1。GPU0为TRAIN:T0，GPU1为INFER；T0在20:28:15.718518观测1140/8000更新，loss=0.1307082772，remaining_train_hours=0.1445449292（约8.7分钟），仅覆盖T0剩余训练，不含端点评价。D2阶段ETA=None，不估计整轮结束时间。

T0是协议必做的clean训练分布控制，可与D2并行；本输出未给T1/T2/T3门禁结果或派发证据。GPU0旧progress/runtime停留在20:26的D1推理，不能用旧文件误判当前GPU0空闲或卡住；当前状态和T0更新时间表明正在训练。两卡峰值allocated约5.54GiB，CPU基准选择32进程、每进程数值库1线程；日志尾部只有配置预期的xFormers警告和D1进度，未见错误，但并非全日志验收。

先读[研究决定](current/RESEARCH_DECISION.md)、[交接](current/HANDOFF.md)、[状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)，再读[最新观测](../records/phase24_registration_20261014/observation_202816.json)、[执行协议](protocols/PHASE_24_EXECUTION_20261014.md)、[科学门禁](protocols/PHASE_24_DIAGNOSIS_AND_CONDITIONAL_HEADS_20261014.md)。

保持原队列自动继续，后续只读查询，不重复登记或重启。研究主线RGB–DSM条件互补与退化/缺失分割不变，恢复旁支。原C/L和B1/B3门禁不改；T0 clean8k必做，T1/T2/T3按门禁，最多4小头32k，0新专家/训练seed。GPU0/1≥24h可续，无硬截止，无SSH/Test6/held4/final或自动失败重试。

新对话先读[本轮接续说明](current/NEW_CHAT_HANDOFF_20261014.md)，再只读查询原队列，勿重复登记。
