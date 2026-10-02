# 当前状态：D25完成并复核

更新2026-10-02。最后服务器观测2026-10-02T15:14:54.351476+08:00：D25 COMPLETE 8/8，全部4000步，summary_exit=0，test6_loaded=false。并非实时PID查询；无新队列启动记录。运行目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d25_missingness_20261002T130253_1358078。

原件已上传GitHub提交2290b39cad802dd96ac980faedc291f5b0611fea，共713文件；固定执行0c31167d0fdb57f03459ea18981c1ee02bcee9f2。[完整分析](../experiments/D25_MISSINGNESS_RESULTS_20261002.md)及[重算证据](../../records/research_d25_review_20261002/compact_analysis.json)核验380下载payload SHA、22源码SHA、2304逐tile/1152 pooled矩阵、328梯度诊断、8组完成及选模绑定。未读取权重/预测字节或重推理。

四项预设机制screen均失败；即使排除D24 D1 clean底线，实用增量门槛也失败。Pair本次确实启用；P3相对幅度对照仅+0.001311pp。P0保留强基线，联合退化信号仅为未采纳诊断。当前具体实现不追加seed/lambda/步数，不重跑D24/D25。

研究阶段为论文可行性探索；光学可用时DSM有益融合/退化缺失/负迁移仍为主问题，C1旁支、部分解冻强基线，最终贡献未冻结。资源/目录/nohup约定沿用；Test6禁读。[下一步](NEXT_EXPERIMENT.md)为问题/机制决策，不是新运行授权。
