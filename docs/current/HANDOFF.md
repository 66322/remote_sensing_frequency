# 当前交接：D27全完成待原件复核，D28已接力评价

## 最新完成/接力观测：2026-10-03 18:34（覆盖18:02进度）

用户完成日志确认D27全部10/10 COMPLETE、summary_exit0，前序终态时间18:22:10.948452+08:00（来自D28 status引用）。D28最后18:34:10.615615+08:00已RUNNING；RGB_anchor物理GPU0完成26/34 tile、DSM_anchor物理GPU1完成27/34，其余五模型待调度。接力已发生，无需重新启动；总结束时间仍随实际模型评价耗时估算。

D27汇总初步判定：G1−G0 S_available -1.768601pp、G1−S1 0.000999、L1−G1 0.006278、C1−L1 -0.101474，分别违反安全/动态/局部/类别原必要分数条件。全部原选模step4000；完整screen/逐tile整数矩阵/fixed8000/损失与信息保留仍待原件上传复核。完成不代表gate通过，不改门槛、追加失败候选训练或用D28复活原主张；D29未排队。当前可只读上传D27记录，同时让D28继续。[初步报告](../experiments/D27_COMPLETION_D28_HANDOVER_PRELIMINARY_20261003.md)。这是最后收到的服务器证据，不保证之后进程实时存活。

## 最新服务器启动观测：2026-10-03 09:22（目录时间）

用户已执行ba7088e联合入口。bootstrap输出确认D27控制器PID2001987、D28控制器PID2002037均已启动，并生成linked_execution.json。D27目录`research_d27_safe_routing_repair_20261003T092243758628_2001983`；D28目录`research_d28_pressure_20261003T092243758628_2001983`；联合目录`research_d27_d28_linked_20261003T092243_1955790`，均在既定工程records下。此为最后收到的启动观测，不代表当前进程仍存活。

当前确认级别仅“两个控制器启动且联合索引生成”；D27首步/worker GPU绑定、D28实际WAITING_D27状态及后续接力尚需queue_status与控制器日志确认。不要重执行联合启动命令。下一步只读查询现有目录；原GPU0/1、nohup/zzx、预算、loss、科学门槛和D29条件规则不变。[启动原件](../../records/research_d27_d28_linked_20261003T092243_1955790/startup_observation.json)。


2026-10-03用户明确要求“一起实现”：D27修复补跑与D28自动后接已实现并完成23项CPU行为检查（D27 15项、D28 8项），新增代码通过Python3.10语法检查。**已收到本次两个控制器启动输出，训练首步与D28等待状态尚待核对。**

研究仍处论文可行性探索，主问题RGB–DSM双方条件互补、退化/缺失可靠分割。安全融合、动态专家、局部类别为待验候选；频率可选，任务驱动恢复旁支，不自动改主线。

[D26完整判定](../experiments/D26_COMPLETE_D27_FAILURE_REVIEW_20261003.md)：最后观测2026-10-03T04:04:45.239849+08:00 COMPLETE9/9，180份主条件tile矩阵独立重算一致。XSF对B0 S+0.156829不足原+0.2，语义不足，selected频率有有限线索但fixed8000错配+0.073522不足；DSM独有正确保留相对X−0.919307。保留普通融合强基线，不重跑D26/增加seed/改门槛。

原D27最后观测2026-10-03T04:12:45.117489+08:00 COMPLETE_WITH_TECHNICAL_FAILURES、0/10；全部step0因worker丢treatment，未更新优化器，没有科学负结果。根因修复及完整CPU反传回归已通过。原失败目录保留；新repair目录原10组×8000、batch16无累积、seed42、原选模/增强/loss/gate不变。

[连续设计](../protocols/D27_D28_LINKED_RESEARCH_PLAN_20261003.md)、[实现验证](../experiments/D27_D28_IMPLEMENTATION_20261003.md)和[NEXT一次nohup命令](NEXT_EXPERIMENT.md)。联合bootstrap写linked_execution.json关联新D27与独立D28目录。D28控制器等待原十组终态+锁释放，再绑固定7模型selected SHA；缺项停在WAITING_EVIDENCE，不替换。224压力+14clean共238次tile、无训练，clean整数矩阵/预测SHA先重现，同边际相关性输入label-free；D29未实现或排队。不把CPU/mock检查写成真实GPU运行。

用户服务器执行，无SSH；根/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro。D26目录research_d26_bidirectional_20261002T191253_1513109；旧D27目录research_d27_safe_routing_after_d26_20261002T191253_1513109。仅GPU0/1 H10080GB，RAM/磁盘充足、nohup、缓存/临时/快照/日志在zzx对应目录，无资源测量。Test6禁读；Val2反复开发、DSM曾暴露held4，非独立final。权重/预测只服务器索引，轻量原件GitHub为准。原门槛失败不能由D28挽救；D29仅待支持后单独冻结。

[上次交接](../history/HANDOFF_before_D27_D28_implementation_20261003.md)。下一助手先读五入口和实际新目录观测，不重新资源审计、不重复启动、不用旧失败目录跨commit resume。当前已收到新控制器PID，仍缺首步/WAITING_D27观测和D27/D28科学结果。
