# START HERE：D26九组已启动，查询已有队列

更新2026-10-02；权威分支rebuild-v1-protocol-20260915。用户已明确授权D26具体执行。主问题仍为RGB外观/纹理/语义与DSM高度/几何双向互补及任一方退化/缺失；频率/语义是待验证机制，最终贡献未冻结。

读取顺序：
1. [研究定位与决定](current/RESEARCH_DECISION.md)
2. [当前交接](current/HANDOFF.md)
3. [当前状态](current/PROJECT_STATUS.md)
4. [下一步](current/NEXT_EXPERIMENT.md)
5. [已有D15—D25结论](experiments/RESEARCH_SYNTHESIS_D15_D25_20261002.md)
6. [冻结D26方案](protocols/D26_BIDIRECTIONAL_FEATURE_PLAN_20261002.md)、[实际执行接口和启动](protocols/D26_EXECUTION_20261002.md)、[文献映射](literature/D26_BIDIRECTIONAL_COMPLEMENTARITY_20261002.md)

D26代码52f94388b1a9c7557e9ef533075661139cd55eda：J0/B0/CAP/X/XS/XF/XSF/shS/shF各8000，共72k；复用D25 P6第2000步RGB与D15 seed42第15000步DSM，不重训单模态。16行为CPU及原DSM接口检查通过，服务器已回传J0/B0训练步，正式评价结果待产出。两H100 GPU0/1、batch16无累积、nohup、所有产物zzx对应新目录；无需资源审计或重问执行许可。固定队列不自动扩展。

最后服务器观测：queue_status为2026-10-02T19:18:19.427139+08:00 RUNNING、COMPLETE0/9；GPU0 J0 training180/8000（19:18:12.689409+08:00），GPU1 B0 training580/8000（19:18:23.902610+08:00）。queue与worker为分别读取的时间戳，B0行更新稍晚；其余七组PENDING。已收到实际训练步，尚无选模/评价指标或原始gradient文件，不作为实时PID查询和精度结论。本次目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d26_bidirectional_20261002T191253_1513109。[启动证据](../records/research_d26_launch_observation_20261002/user_reported_launch.json)。不再重复启动。D23—D25失败配方关闭保持，C1旁支，Test6禁读，反复开发Val2/历史held4不独立final。长结果轻量原件上传GitHub再读，checkpoint/预测留服务器并索引。


## 2026-10-02 19:18进度同步与结论边界

[逐任务观测](../records/research_d26_progress_20261002T191819/observation.json)、[用户输出](../records/research_d26_progress_20261002T191819/user_status_stdout.txt)、[暂估结束时间](../records/research_d26_progress_20261002T191819/eta_estimate.json)已提交。controller PID1571946及本次目录保持，不重复启动。当前只有运行推进证据，D26没有新增精度/频率/语义贡献结论；既有D15—D25结论已在GitHub记录，不因本轮运行改变。

截至本次回传，整轮暂估还需8–12小时，约10月3日03:00–07:00；这是早期速度外推，后续交互/完整评价尚未计时，服务端仍报告ETA_PENDING。第一正常任务完整结束后更新，不额外资源探针。以本分支共享记录为准，不能只留本地或聊天；checkpoint/预测/完整实时日志仍在服务器，完成后上传轻量评价原件再分析。


## 2026-10-02近期文献阅读补充

[双向互补、缺失补偿与频率机制阅读](literature/D26_RECENT_PAPERS_MECHANISM_READING_20261002.md)补充KTB、DIS2、SGMA、功能熵、MFFNet/FDAM、EBMC和SynIB的机制边界。新增建议为独有信息保持、双向任务补偿与编码频率衰减的条件检验，均未采纳为新运行/贡献。D26固定九组及去留规则不变；完成后优先用现有结果定位瓶颈，按证据选择至多一项，不重启资源审计或重复单模态训练。最后服务器状态仍以已归档观测为准。
