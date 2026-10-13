# 当前交接：CPU113/160，继续汇总并接收原件（2026-10-13）

## 最后观测与下一步

最后用户只读查询 **2026-10-13T11:18:34.988820+08:00**；queue LAST_OBSERVED **11:18:34.620128**，CPU_ORACLE_AND_CONDITIONAL_COUNTS/controller LIVE=True，GPU100 COMPLETE。D progress **11:18:34.471223**：**113/160**，tile5_10/realization9/random，2CPU进程，保留63、新增50、累计843.702853秒。剩47，按当前合计吞吐16.874秒/case约13.2分钟，D条件ETA11:31–11:35，之后原五项汇总未计时；不是实时状态或整轮完成保证。pixel/matched两个真实case全result exact PASS已收到用户摘录，完整原件尚未上传/独立验收。

原目录 `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase15_recoverability_20261012T233532_842792`；推理commit45138f0f92c668bc86ce9532a4382b38d2b12b6d。CPU加速子目录 `cpu_acceleration_20261013T110244_1189050`、登记PID1189233，执行commit4842b5eb38c62b19db97094d88526260f5fe3359，后续日志为子目录controller.log，原nohup为历史。原失败目录research_phase15_recoverability_20261012T232212_836118保留。不要再次enqueue/accelerate。

保持既有CPU任务，D完成后自动原五项汇总→PHASE15_COMPLETE_AWAITING_REVIEW。原status_phase15.py及analysis/D/progress.json仍可查；完成/进程锁退出后前台upload_phase15.py --directory DIR --root ROOT上传轻量原件。当前没有完整summary/科学分数，不按进度或两case等价宣称论文贡献。

## 资源使用决定

2026-10-13用户要求充分使用内存、并行分析和实验数据预加载，并回传free -h：total1.9Ti/available1.8Ti/used11Gi/free1.8Ti/shared2.3Gi/buff-cache19Gi/swap0。仅用户主机free输出，无独立时间戳/容器quota/affinity回报，不直接当进程可用内存或CPU核数。已将大内存驻留与并行作为后续默认工程策略：CPU case并行初选8（受实际CPU quota/affinity及内存限制并经小规模吞吐校准），工作集按清单一次SHA校验/解压、只读驻留并复用，必要时共享只读cache避免重复副本。缓存预算≤实际可用内存50%，预留数值临时数组和其他任务资源，不为“吃满”强制分配。数值库每进程线程数与case进程数分开控制，不直接把OMP改成最大值。

源码核对：Post-T训练已经fit12全tile驻留、PrefetchedBatches(16,8,4,True)，8线程共享内存crop预取、4batch预取及pin_memory/non_blocking传输；不是每步重读磁盘。后续优化先测data-wait/计算时间，再调预取；保持batch/采样序列/seed/精度/训练预算/验证口径及batch_hash不变。

已新增ResidentArrayCache与recommended_profile工程组件，2项CPU检查通过（16次8线程请求仅装载1次、15命中、数组一致且只读、SHA/修改拒绝、预算/资源限制），尚未接入当前immutable运行或服务器实测；不能写成当前全部预测已驻留。当前只剩47case、约13分钟，决定继续现有2进程而不做第二次接管/全量预加载，避免打断接近结束的队列。新缓存/并发策略用于后续独立执行包，不改变科学主线或新增训练任务。

## 科学角色和边界

主线仍RGB–DSM双向条件互补与退化/缺失分割；任务驱动恢复旁支。唯一当前研究问题可恢复性分解E/A/B/C/D，routing与residual context均为条件候选。当前0训练、100固定GPU工作批/1540逻辑case、160D统计case，无自动新seed/Test6/held4/final；用户允许GPU0/1、至少一天且未完继续，无24h截止。不为填时长追加任务。

旧Post-T最后上传观测2026-10-12 11:03:22.917566+08:00：8/8COMPLETE/PAIRED_SCREEN=False；Structured 16:32:44.762198：42/42COMPLETE/NO_SUPPORT_THIS_PROTOCOL。R16−H16+0.348562pp局部通过，整体失败来自5/6 E−R0底线；S1主PE+0.122522pp CI跨0，不重开旧gate、不盲目续训。科学问题、路线角色、去留条件以RESEARCH_DECISION与原协议/证据为准。

先读[研究决定](RESEARCH_DECISION.md)、[新交接](NEW_CHAT_HANDOFF_20261011.md)、[CPU接管协议](../protocols/PHASE_1_5_CPU_ACCELERATION_20261013.md)、[资源策略](../protocols/LARGE_MEMORY_PARALLEL_POLICY_20261013.md)、[主诊断设计](../protocols/PHASE_1_5_RECOVERABILITY_20261012.md)、[实验索引](../experiments/rebuild_v1/INDEX.md)。。上一版含历史进度的入口已归档[HANDOFF.md历史版](../history/pre_resource_policy_20261013/HANDOFF.md)。
