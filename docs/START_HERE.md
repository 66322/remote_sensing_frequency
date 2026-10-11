# 共享入口：R8终点评价，原队列将自动进入16k

2026-10-11新增[结构化缺失设计评审草案](protocols/STRUCTURED_FAILURE_EVAL_V0_20261011.md)，来源为用户要求综合分析所附规划；属于重写版建议，尚未实现、冻结或登记。建议先完成当前F/H/R验收，再做4系统×4掩码家族×20实现×2tile＝640缺失case＋8clean的零训练核心诊断。S1-3−S1-0不作纯上下文效应；改用同权重M000 masked/context；随机块与语义匹配twin分开；不自动20→40，不凭新评价改选R16。研究主线、旧门槛与现有队列不变。

权威分支：66322/remote_sensing_frequency，rebuild-v1-protocol-20260915。

最后服务器只读查询2026-10-11T23:34:24.796568+08:00：queue观测23:34:17.832878、RUNNING、controller LIVE=True。CONTENT_PRE/H8/F8 COMPLETE且worker退出；H8/F8均8000步。R8 GPU1 RUNNING/LIVE=True、8000/8000、phase=endpoint_ordinary（3_11/aux_down4，529/529窗口仅指该case）。R16/H16/F16/CONTENT_POST PENDING。3/8整项完成、1项评价中、4项待办；训练更新回报24000/72000，R8尚未完成整项技术验收。此为最后观测，不代表实时状态。

H8/F8完整worker耗时10338.760/10277.432秒（约2h52m/2h51m）；R8当前6936.955秒且仍评价。remaining_train_hours=0仅表示训练步数已满，不表示任务已结束。没有本轮精度或DSM内容原件，loss差不能作方法结论。

GPU0空闲可由原8k→16k阶段依赖解释；status回报未包含gpu_blocked字段，不能仅据利用率断言release状态。控制器需H8/F8/R8整项COMPLETE并完成三组batch配对检查后才派发16k。若两卡启用、无外部占卡且技术检查通过，按现代码GPU0→R16、GPU1→H16，先完成卡→F16。无需重复enqueue、rejoin或手动启动worker。

[23:34进度回报](../records/research_post_t_paired_v2_20261011T182543_3880702/user_reported_progress_20261011T233424.json)、[具体排期](protocols/POST_T_PAIRED_RESOURCE_SCHEDULE_20261011.md)。原目录/执行44e4df5a保持，前测及训练精度原件仍待完整后验收。

用户最新资源决定：GPU0＋GPU1，预留一天以上，未完成继续；需要其中一张卡时保存退出该卡任务，未完成部分与待运行任务转到另一张卡排队续跑。释放卡显式rejoin前不再接任务。这覆盖旧只GPU0限制；无SSH，仍由用户执行终端。

六组F/H/R×8k/16k，共72000优化器调用；前后各24个0训练DSM内容case。阶段CONTENT_PRE→[H8,F8,R8]→[R16,H16,F16]→CONTENT_POST，阶段内双卡派发，8k后不按分数筛长预算。代码、完整配置、CPU合成检查和控制/上传入口已就绪；真实GPU/权重验收在服务器执行链中完成。

[执行、释放显卡、查询与上传](protocols/POST_T_PAIRED_V2_EXECUTION_20261011.md)、[科学细则v2](protocols/POST_T_PAIRED_ADAPTATION_BUDGET_20261011.md)、[研究排期](protocols/POST_T_RESEARCH_SEQUENCE_20261011.md)、[实现检查](../records/post_t_paired_v2_implementation_20261011/verification.json)、[设计索引](../records/post_t_research_plan_v2_20261011/design.json)。

主线仍RGB–DSM双向条件互补与退化/缺失分割，恢复为旁支。已验证线索限重复Val2/seed42/已知RGB局部缺失，旧T7/U/E失败不改；双向、独立泛化与容量解释未解决。[完整T](experiments/POST_T_FULL_RESULTS_20261011.md)、[机制结果](experiments/POST_T_MECHANISM_RESULTS_20261011.md)。禁Test6/held4/final，不自动失败重试/加seed/扩族。记录在/home/jovyan/zzx对应目录。

读取顺序：[新对话交接](current/NEW_CHAT_HANDOFF_20261011.md)→[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[PROJECT_STATUS](current/PROJECT_STATUS.md)→[NEXT_EXPERIMENT](current/NEXT_EXPERIMENT.md)→[实验索引](experiments/rebuild_v1/INDEX.md)。
