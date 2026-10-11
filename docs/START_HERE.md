# 共享入口：H8/F8双卡训练已确认

权威分支：66322/remote_sensing_frequency，rebuild-v1-protocol-20260915。

最后服务器只读查询2026-10-11T18:54:08.952037+08:00：queue RUNNING、controller LIVE=True；CONTENT_PRE已COMPLETE退出（worker约20分52秒），H8 GPU0与F8 GPU1同时RUNNING/LIVE=True，各180/8000步。1/8整项完成、2运行、5待办。两卡训练派发确认；此为最后观测，不代表实时状态。

H/F训练步速约0.663/0.653秒，peak_allocated约12.8/12.4GiB；各自约1.44/1.42h的剩余预测只含训练计算，不含后续验证/评价，整队及R步速未校准。前测原件、训练指标及完整机制结论尚未验收。[本次回报](../records/research_post_t_paired_v2_20261011T182543_3880702/user_reported_progress_20261011T185408.json)。原目录/执行44e4df5a保持，继续原双卡队列；按需要才release，不重复启动。

用户最新资源决定：GPU0＋GPU1，预留一天以上，未完成继续；需要其中一张卡时保存退出该卡任务，未完成部分与待运行任务转到另一张卡排队续跑。释放卡显式rejoin前不再接任务。这覆盖旧只GPU0限制；无SSH，仍由用户执行终端。

六组F/H/R×8k/16k，共72000优化器调用；前后各24个0训练DSM内容case。阶段CONTENT_PRE→[H8,F8,R8]→[R16,H16,F16]→CONTENT_POST，阶段内双卡派发，8k后不按分数筛长预算。代码、完整配置、CPU合成检查和控制/上传入口已就绪；真实GPU/权重验收在服务器执行链中完成。

[执行、释放显卡、查询与上传](protocols/POST_T_PAIRED_V2_EXECUTION_20261011.md)、[科学细则v2](protocols/POST_T_PAIRED_ADAPTATION_BUDGET_20261011.md)、[研究排期](protocols/POST_T_RESEARCH_SEQUENCE_20261011.md)、[实现检查](../records/post_t_paired_v2_implementation_20261011/verification.json)、[设计索引](../records/post_t_research_plan_v2_20261011/design.json)。

主线仍RGB–DSM双向条件互补与退化/缺失分割，恢复为旁支。已验证线索限重复Val2/seed42/已知RGB局部缺失，旧T7/U/E失败不改；双向、独立泛化与容量解释未解决。[完整T](experiments/POST_T_FULL_RESULTS_20261011.md)、[机制结果](experiments/POST_T_MECHANISM_RESULTS_20261011.md)。禁Test6/held4/final，不自动失败重试/加seed/扩族。记录在/home/jovyan/zzx对应目录。

读取顺序：[新对话交接](current/NEW_CHAT_HANDOFF_20261011.md)→[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[PROJECT_STATUS](current/PROJECT_STATUS.md)→[NEXT_EXPERIMENT](current/NEXT_EXPERIMENT.md)→[实验索引](experiments/rebuild_v1/INDEX.md)。
