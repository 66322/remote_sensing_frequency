# START HERE：D27全完成，D28已接力；D27主张初步不满足原门槛

## 最新完成/接力观测：2026-10-03 18:34（覆盖18:02进度）

用户完成日志确认D27全部10/10 COMPLETE、summary_exit0，前序终态时间18:22:10.948452+08:00（来自D28 status引用）。D28最后18:34:10.615615+08:00已RUNNING；RGB_anchor物理GPU0完成26/34 tile、DSM_anchor物理GPU1完成27/34，其余五模型待调度。接力已发生，无需重新启动；总结束时间仍随实际模型评价耗时估算。

D27汇总初步判定：G1−G0 S_available -1.768601pp、G1−S1 0.000999、L1−G1 0.006278、C1−L1 -0.101474，分别违反安全/动态/局部/类别原必要分数条件。全部原选模step4000；完整screen/逐tile整数矩阵/fixed8000/损失与信息保留仍待原件上传复核。完成不代表gate通过，不改门槛、追加失败候选训练或用D28复活原主张；D29未排队。当前可只读上传D27记录，同时让D28继续。[初步报告](experiments/D27_COMPLETION_D28_HANDOVER_PRELIMINARY_20261003.md)。这是最后收到的服务器证据，不保证之后进程实时存活。

## 最新服务器启动观测：2026-10-03 09:22（目录时间）

用户已执行ba7088e联合入口。bootstrap输出确认D27控制器PID2001987、D28控制器PID2002037均已启动，并生成linked_execution.json。D27目录`research_d27_safe_routing_repair_20261003T092243758628_2001983`；D28目录`research_d28_pressure_20261003T092243758628_2001983`；联合目录`research_d27_d28_linked_20261003T092243_1955790`，均在既定工程records下。此为最后收到的启动观测，不代表当前进程仍存活。

当前确认级别仅“两个控制器启动且联合索引生成”；D27首步/worker GPU绑定、D28实际WAITING_D27状态及后续接力尚需queue_status与控制器日志确认。不要重执行联合启动命令。下一步只读查询现有目录；原GPU0/1、nohup/zzx、预算、loss、科学门槛和D29条件规则不变。[启动原件](../records/research_d27_d28_linked_20261003T092243_1955790/startup_observation.json)。


权威分支rebuild-v1-protocol-20260915，2026-10-03更新。读[研究决定](current/RESEARCH_DECISION.md)→[交接](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)。

2026-10-03用户明确要求“一起实现”：D27修复补跑与D28自动后接已实现并完成23项CPU行为检查（D27 15项、D28 8项），新增代码通过Python3.10语法检查。**已收到本次两个控制器启动输出，训练首步与D28等待状态尚待核对。**

执行范围：D27原十组修复补跑→D28固定七模型224压力+14clean评价；两个独立目录、一次nohup联合入口，D27终态+控制器锁释放+所需selected SHA齐全才接力。D29不自动启动。[代码/检查说明](experiments/D27_D28_IMPLEMENTATION_20261003.md)、[冻结连续协议](protocols/D27_D28_LINKED_RESEARCH_PLAN_20261003.md)。

[D26完整复核/原D27根因](experiments/D26_COMPLETE_D27_FAILURE_REVIEW_20261003.md)：D26最后观测04:04:45 COMPLETE9/9，当前主候选原门槛未过，不重跑；原D2704:12:45全十组step0技术失败，无科学结果。新运行保留原快照，不旧目录跨提交resume、不把失败改写已完成。

仅GPU0/1 H10080GB、内存/磁盘充足、所有缓存/临时/记录/代码快照在zzx相应目录。无需资源审计；禁止Test6、Val2不独立final。原负结果与原门槛保留，频率可选、任务驱动恢复仍旁支。轻量记录同步GitHub，预测/checkpoint保留服务器索引。
