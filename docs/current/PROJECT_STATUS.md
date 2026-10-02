# 当前状态：D26已启动，最后观测initializing step0

更新2026-10-02。最后服务器观测：2026-10-02本次用户回传，controller PID1571946；GPU0 J0 PID1571983、GPU1 B0 PID1571989，均initializing step=0。目录创建19:12:53+08:00来自目录名，日志行无精确观测时间；不表述为实时PID状态或已完成首batch。本次目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d26_bidirectional_20261002T191253_1513109；[启动证据](../../records/research_d26_launch_observation_20261002/user_reported_launch.json)。首训练步/加载验收/梯度检查待回传，仅查询已有队列。

历史D25最后观测2026-10-02T15:14:54.351476+08:00 COMPLETE8/8，全部4000步，summary_exit=0。

原件已上传GitHub提交2290b39cad802dd96ac980faedc291f5b0611fea，共713文件；固定执行0c31167d0fdb57f03459ea18981c1ee02bcee9f2。[完整分析](../experiments/D25_MISSINGNESS_RESULTS_20261002.md)及[重算证据](../../records/research_d25_review_20261002/compact_analysis.json)核验380下载payload SHA、22源码SHA、2304逐tile/1152 pooled矩阵、328梯度诊断、8组完成及选模绑定。未读取权重/预测字节或重推理。

四项预设机制screen均失败；即使排除D24 D1 clean底线，实用增量门槛也失败。Pair本次确实启用；P3相对幅度对照仅+0.001311pp。P0保留强基线，联合退化信号仅为未采纳诊断。当前具体实现不追加seed/lambda/步数，不重跑D24/D25。

研究阶段为论文可行性探索。本轮用户明确纠正为RGB与DSM双方信息互补、任一方退化/缺失的主问题；此前RGB可用限制只描述旧轮范围。单模态历史已充分记录，不能重复安排。[D26](../protocols/D26_BIDIRECTIONAL_FEATURE_PLAN_20261002.md)已获用户明确具体执行授权，九组×8000已实现，代码52f94388b1a9c7557e9ef533075661139cd55eda；16CPU行为及原DSM接口检查通过，已收到D26初始化启动观测，真实权重/CUDA首batch待验证。[现有队列查询与上传](../protocols/D26_EXECUTION_20261002.md)，batch16无累积、GPU0/1动态队列、所有产物zzx新实验目录；不重复资源审计或单模态训练。C1旁支、部分解冻强基线，最终贡献未冻结。资源/目录/nohup约定沿用；Test6禁读。
