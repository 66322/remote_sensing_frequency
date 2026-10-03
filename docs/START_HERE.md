# START HERE：D27补跑与D28自动后接已实现，待服务器启动观测

权威分支rebuild-v1-protocol-20260915，2026-10-03更新。读[研究决定](current/RESEARCH_DECISION.md)→[交接](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)。

2026-10-03用户明确要求“一起实现”：D27修复补跑与D28自动后接已实现并完成23项CPU行为检查（D27 15项、D28 8项），新增代码通过Python3.10语法检查。**尚无本次服务器启动观测，不能写成已运行或已经排队。**

执行范围：D27原十组修复补跑→D28固定七模型224压力+14clean评价；两个独立目录、一次nohup联合入口，D27终态+控制器锁释放+所需selected SHA齐全才接力。D29不自动启动。[代码/检查说明](experiments/D27_D28_IMPLEMENTATION_20261003.md)、[冻结连续协议](protocols/D27_D28_LINKED_RESEARCH_PLAN_20261003.md)。

[D26完整复核/原D27根因](experiments/D26_COMPLETE_D27_FAILURE_REVIEW_20261003.md)：D26最后观测04:04:45 COMPLETE9/9，当前主候选原门槛未过，不重跑；原D2704:12:45全十组step0技术失败，无科学结果。新运行保留原快照，不旧目录跨提交resume、不把失败改写已完成。

仅GPU0/1 H10080GB、内存/磁盘充足、所有缓存/临时/记录/代码快照在zzx相应目录。无需资源审计；禁止Test6、Val2不独立final。原负结果与原门槛保留，频率可选、任务驱动恢复仍旁支。轻量记录同步GitHub，预测/checkpoint保留服务器索引。
