# 当前交接：D25已完成，关闭四项具体实现确认路径

更新2026-10-02。权威分支rebuild-v1-protocol-20260915；[此前交接](../history/HANDOFF_20261002_BEFORE_D25_COMPLETE_REVIEW.md)存档。不要把历史“待启动”当当前状态，不重复启动、上传或资源测量。

最后观测2026-10-02T15:14:54.351476+08:00：D25 COMPLETE 8/8（13:02至15:14，约2h12）。执行代码0c31167d0fdb57f03459ea18981c1ee02bcee9f2；原件2290b39cad802dd96ac980faedc291f5b0611fea已上传；服务器目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d25_missingness_20261002T130253_1358078。[结果报告](../experiments/D25_MISSINGNESS_RESULTS_20261002.md)、[离线重算](../../records/research_d25_review_20261002/compact_analysis.json)、[冻结协议](../protocols/D25_MISSINGNESS_OPTIMIZATION_PLAN_20261002.md)。

P1 Pair真实启用4000步但composite对P0−0.063747pp；D24 A1/A3无效消融历史保留，不能混为同一负结果。P2分头对P0/P5综合约+0.05pp；P3对P2+0.006644、对P7+0.001311pp；P4对P0+0.005320pp。四screen均失败，且不是仅clean底线导致。41梯度采样P0无冲突、P3一次，不外推全部步骤。按已授权预设规则关闭这些实现的确认预算，不扫参数或加seed。

P0对同M0光学P6综合+0.441132pp，但整幅DSM缺失−0.260187pp，保留普通last4/QD强基线。分头对联合退化压力改善约0.45–0.59pp，但zero时接近独立光学，中心局部缺失有损失；新增压力条件不参与原screen，这只是未采纳线索。选中步差异及Q/QD/容量边界见报告。原计数/选模元数据已复核，权重与预测未重推理。

主问题未变，C1恢复旁支、部分解冻强基线、最终贡献未冻结；本轮未永久否定频率/语义或自动转向恢复。下一工作解决辅助信息可归因性、回退光学差距、联合退化与局部缺失取舍；另立高信息量方案后才可能确认。新方案/训练未采纳，授权固定八组已用完，不默认扩展。

GPU0/1 H10080GB、RAM/硬盘充足；长任务nohup，全部代码/cache/log/产物在zzx对应目录。无SSH，由用户终端运行；不重复资源准入审计。Test6禁读，反复Val2及Train16暴露held4不独立final。
