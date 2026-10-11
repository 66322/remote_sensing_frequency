# 项目状态：R8终点评价，原队列将自动进入16k

2026-10-11新增[结构化缺失设计评审草案](../protocols/STRUCTURED_FAILURE_EVAL_V0_20261011.md)，来源为用户要求综合分析所附规划；属于重写版建议，尚未实现、冻结或登记。建议先完成当前F/H/R验收，再做4系统×4掩码家族×20实现×2tile＝640缺失case＋8clean的零训练核心诊断。S1-3−S1-0不作纯上下文效应；改用同权重M000 masked/context；随机块与语义匹配twin分开；不自动20→40，不凭新评价改选R16。研究主线、旧门槛与现有队列不变。

权威共享源：66322/remote_sensing_frequency，rebuild-v1-protocol-20260915；本地仅工作副本。

最后服务器只读查询2026-10-11T23:34:24.796568+08:00：queue观测23:34:17.832878、RUNNING、controller LIVE=True。CONTENT_PRE/H8/F8 COMPLETE且worker退出；H8/F8均8000步。R8 GPU1 RUNNING/LIVE=True、8000/8000、phase=endpoint_ordinary（3_11/aux_down4，529/529窗口仅指该case）。R16/H16/F16/CONTENT_POST PENDING。3/8整项完成、1项评价中、4项待办；训练更新回报24000/72000，R8尚未完成整项技术验收。此为最后观测，不代表实时状态。

H8/F8完整worker耗时10338.760/10277.432秒（约2h52m/2h51m）；R8当前6936.955秒且仍评价。remaining_train_hours=0仅表示训练步数已满，不表示任务已结束。没有本轮精度或DSM内容原件，loss差不能作方法结论。

GPU0空闲可由原8k→16k阶段依赖解释；status回报未包含gpu_blocked字段，不能仅据利用率断言release状态。控制器需H8/F8/R8整项COMPLETE并完成三组batch配对检查后才派发16k。若两卡启用、无外部占卡且技术检查通过，按现代码GPU0→R16、GPU1→H16，先完成卡→F16。无需重复enqueue、rejoin或手动启动worker。

[23:34进度回报](../../records/research_post_t_paired_v2_20261011T182543_3880702/user_reported_progress_20261011T233424.json)、[具体排期](../protocols/POST_T_PAIRED_RESOURCE_SCHEDULE_20261011.md)。原目录/执行44e4df5a保持，前测及训练精度原件仍待完整后验收。

研究阶段为可行性探索与机制定位。主线仍RGB–DSM双向条件互补与退化/缺失分割，恢复为旁支。已验线索限Potsdam fit12→重复Val2 3_11/5_10、seed42、已知RGB局部缺失；DSM_U为保护结果。旧T7/U/E=False保持，不后验换M303/T5，不声称双向、未知故障或独立泛化。

用户已要求具体安排并执行准备；最新明确授权GPU0＋GPU1、预留一天以上、24h后未完成继续。需要哪张卡时，该卡任务保存后退出；未完成部分与待运行任务自动在另一张卡排队续跑。被释放卡保持停用，显式rejoin后才参与派发。此授权覆盖旧“只GPU0”资源限制，研究配方、seed与门槛不变。

六组F/H/R×8k/16k、72000优化器调用，主候选R16；前后各24内容诊断case、0更新。阶段顺序CONTENT_PRE→[H8,F8,R8]→[R16,H16,F16]→CONTENT_POST；方括号内为共享队列优先顺序，每张可用卡一个worker，已保存的续跑优先。8k三组技术完整且batch配对通过后才进16k，不按8k分数筛选。

H训练私有RGB net.rgb与decoder[:-1]；R另开末4编码块；最终分类器decoder[-1]冻结。6组统一S1-0初值、独立新优化器，同组真实batch散列配对；8k/16k为预算×日程比较。容量差异及DSM内容破坏的解释边界保留。X8/X16不可自动派发，DSM镜像/新频域/恢复扩张/多seed均未采纳。

代码已实现：六份完整配置、真实梯度/冻结契约、逐step输入散列、每500状态/每4000绑定验证、固定终点与次要选模、C端点复现、双卡控制及原件上传。本地CPU合成检查通过，包含单卡释放后跨卡续跑调度与优化器/RNG恢复；不等于真实H100、实权重或跨CUDA逐位一致验收。旧26项只查完成/进程/绑定，不重复登记或训练。

[执行与操作说明](../protocols/POST_T_PAIRED_V2_EXECUTION_20261011.md)、[配对细则](../protocols/POST_T_PAIRED_ADAPTATION_BUDGET_20261011.md)、[研究排期](../protocols/POST_T_RESEARCH_SEQUENCE_20261011.md)、[机制结果](../experiments/POST_T_MECHANISM_RESULTS_20261011.md)、[实现验收](../../records/post_t_paired_v2_implementation_20261011/verification.json)、[此前交接归档](../history/POST_T_PAIRED_V2_PRE_EXECUTION_HANDOFF_20261011.md)。

立即下一步：继续R8终点评价，8k三组全部技术完整且配对通过后自动进入16k；两卡启用空闲时GPU0接R16、GPU1接H16，先完成卡接F16。只有用户需要用卡时才release，未完成任务在剩余卡排队续跑。无SSH、不重复登记/启动，不主动测试迁移。完整后显式上传轻量原件并独立验收，Test6/held4/final关闭。

预留一天以上，无全队24h截止；完成固定任务后自动停。单臂累计活跃时间保护仍为8k 12h、16k 24h、内容批次4h，排队/主动释放等待不计。OOM/绑定/非有限/技术失败HOLD，保留现场且不自动重试；主动释放属于同一任务续跑。完整后显式上传轻量原件，再独立复算全部配对、轨迹、内容与保护并制定后继，不能把本地检查写为实验已验证。
