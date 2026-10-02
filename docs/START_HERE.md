# START HERE：D26九组已启动，查询已有队列

更新2026-10-02；权威分支rebuild-v1-protocol-20260915。用户已明确授权D26具体执行。主问题仍为RGB外观/纹理/语义与DSM高度/几何双向互补及任一方退化/缺失；频率/语义是待验证机制，最终贡献未冻结。

读取顺序：
1. [研究定位与决定](current/RESEARCH_DECISION.md)
2. [当前交接](current/HANDOFF.md)
3. [当前状态](current/PROJECT_STATUS.md)
4. [下一步](current/NEXT_EXPERIMENT.md)
5. [已有D15—D25结论](experiments/RESEARCH_SYNTHESIS_D15_D25_20261002.md)
6. [冻结D26方案](protocols/D26_BIDIRECTIONAL_FEATURE_PLAN_20261002.md)、[实际执行接口和启动](protocols/D26_EXECUTION_20261002.md)、[文献映射](literature/D26_BIDIRECTIONAL_COMPLEMENTARITY_20261002.md)

D26代码52f94388b1a9c7557e9ef533075661139cd55eda：J0/B0/CAP/X/XS/XF/XSF/shS/shF各8000，共72k；复用D25 P6第2000步RGB与D15 seed42第15000步DSM，不重训单模态。16行为CPU及原DSM接口检查通过，真实GPU首batch待观测。两H100 GPU0/1、batch16无累积、nohup、所有产物zzx对应新目录；无需资源审计或重问执行许可。固定队列不自动扩展。

最后服务器观测：2026-10-02本次用户回传，controller PID1571946；GPU0 J0 PID1571983、GPU1 B0 PID1571989，均initializing step=0。目录创建19:12:53+08:00来自目录名，日志行无精确观测时间；不表述为实时PID状态或已完成首batch。本次目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d26_bidirectional_20261002T191253_1513109。[启动证据](../records/research_d26_launch_observation_20261002/user_reported_launch.json)。不再重复启动。D23—D25失败配方关闭保持，C1旁支，Test6禁读，反复开发Val2/历史held4不独立final。长结果轻量原件上传GitHub再读，checkpoint/预测留服务器并索引。
