# 共享入口：双卡配对执行包就绪，真实运行待回报

权威分支：66322/remote_sensing_frequency，rebuild-v1-protocol-20260915。

最后服务器查询2026-10-11T13:48:26.474610+08:00：旧Post-T 26/26完整且进程退出。原件57ef5ad9已验收；这是最后观测。新执行包READY_NOT_REGISTERED_GPU_RUNTIME_UNVERIFIED，尚未收到新目录/PID/启动回报。

用户最新资源决定：GPU0＋GPU1，预留一天以上，未完成继续；需要其中一张卡时保存退出该卡任务，未完成部分与待运行任务转到另一张卡排队续跑。释放卡显式rejoin前不再接任务。这覆盖旧只GPU0限制；无SSH，仍由用户执行终端。

六组F/H/R×8k/16k，共72000优化器调用；前后各24个0训练DSM内容case。阶段CONTENT_PRE→[H8,F8,R8]→[R16,H16,F16]→CONTENT_POST，阶段内双卡派发，8k后不按分数筛长预算。代码、完整配置、CPU合成检查和控制/上传入口已就绪；真实GPU/权重验收在服务器执行链中完成。

[执行、释放显卡、查询与上传](protocols/POST_T_PAIRED_V2_EXECUTION_20261011.md)、[科学细则v2](protocols/POST_T_PAIRED_ADAPTATION_BUDGET_20261011.md)、[研究排期](protocols/POST_T_RESEARCH_SEQUENCE_20261011.md)、[实现检查](../records/post_t_paired_v2_implementation_20261011/verification.json)、[设计索引](../records/post_t_research_plan_v2_20261011/design.json)。

主线仍RGB–DSM双向条件互补与退化/缺失分割，恢复为旁支。已验证线索限重复Val2/seed42/已知RGB局部缺失，旧T7/U/E失败不改；双向、独立泛化与容量解释未解决。[完整T](experiments/POST_T_FULL_RESULTS_20261011.md)、[机制结果](experiments/POST_T_MECHANISM_RESULTS_20261011.md)。禁Test6/held4/final，不自动失败重试/加seed/扩族。记录在/home/jovyan/zzx对应目录。

读取顺序：[新对话交接](current/NEW_CHAT_HANDOFF_20261011.md)→[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[PROJECT_STATUS](current/PROJECT_STATUS.md)→[NEXT_EXPERIMENT](current/NEXT_EXPERIMENT.md)→[实验索引](experiments/rebuild_v1/INDEX.md)。
