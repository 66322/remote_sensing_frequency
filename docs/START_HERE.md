# START HERE：D27正在训练，D28已实际排队等待

## 最新运行观测：2026-10-03 09:25（覆盖09:22启动待核对状态）

用户贴出的controller/status证据确认：D27于09:25:44.908530+08:00为RUNNING、0/10完成；G0在物理GPU0（PID2002029）training 220/8000，progress_at09:25:49.587334；G1在物理GPU1（PID2002032）training 200/8000，progress_at09:25:40.677921。其余八组PENDING。两个任务均已越过原首次objective的treatment错误，尚未完成训练或获得科学结果。

D28于09:25:45.014090+08:00确认为WAITING_D27、0/7完成，前序RUNNING，七个评价任务PENDING。因此已经实际排队等待；D27结束后的锁释放、checkpoint绑定及自动接力仍待后续观测。D28等待期间不启动推理；D29未排队。当前无需再次启动、资源探针或改动运行设置。ETA等待首个正常任务完成后估算。G0 progress时间晚于controller时间是独立读取worker进度，非同一瞬间快照。此为最后收到的服务器证据，不保证之后持续存活。

[本次运行原件](../records/research_d27_d28_linked_20261003T092243_1955790/training_wait_observation_20261003T092545.json)。仅GPU0/1、nohup及zzx对应目录、原预算/选模/门槛持续有效。


## 最新服务器启动观测：2026-10-03 09:22（目录时间）

用户已执行ba7088e联合入口。bootstrap输出确认D27控制器PID2001987、D28控制器PID2002037均已启动，并生成linked_execution.json。D27目录`research_d27_safe_routing_repair_20261003T092243758628_2001983`；D28目录`research_d28_pressure_20261003T092243758628_2001983`；联合目录`research_d27_d28_linked_20261003T092243_1955790`，均在既定工程records下。此为最后收到的启动观测，不代表当前进程仍存活。

当前确认级别仅“两个控制器启动且联合索引生成”；D27首步/worker GPU绑定、D28实际WAITING_D27状态及后续接力尚需queue_status与控制器日志确认。不要重执行联合启动命令。下一步只读查询现有目录；原GPU0/1、nohup/zzx、预算、loss、科学门槛和D29条件规则不变。[启动原件](../records/research_d27_d28_linked_20261003T092243_1955790/startup_observation.json)。


权威分支rebuild-v1-protocol-20260915，2026-10-03更新。读[研究决定](current/RESEARCH_DECISION.md)→[交接](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)。

2026-10-03用户明确要求“一起实现”：D27修复补跑与D28自动后接已实现并完成23项CPU行为检查（D27 15项、D28 8项），新增代码通过Python3.10语法检查。**已收到本次两个控制器启动输出，训练首步与D28等待状态尚待核对。**

执行范围：D27原十组修复补跑→D28固定七模型224压力+14clean评价；两个独立目录、一次nohup联合入口，D27终态+控制器锁释放+所需selected SHA齐全才接力。D29不自动启动。[代码/检查说明](experiments/D27_D28_IMPLEMENTATION_20261003.md)、[冻结连续协议](protocols/D27_D28_LINKED_RESEARCH_PLAN_20261003.md)。

[D26完整复核/原D27根因](experiments/D26_COMPLETE_D27_FAILURE_REVIEW_20261003.md)：D26最后观测04:04:45 COMPLETE9/9，当前主候选原门槛未过，不重跑；原D2704:12:45全十组step0技术失败，无科学结果。新运行保留原快照，不旧目录跨提交resume、不把失败改写已完成。

仅GPU0/1 H10080GB、内存/磁盘充足、所有缓存/临时/记录/代码快照在zzx相应目录。无需资源审计；禁止Test6、Val2不独立final。原负结果与原门槛保留，频率可选、任务驱动恢复仍旁支。轻量记录同步GitHub，预测/checkpoint保留服务器索引。
