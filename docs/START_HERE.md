# 共享入口：N2与E0/E1/E2已完成，先上传原件分析

最后服务器观测（用户2026-10-06回传）：queue_status观测时间2026-10-05T23:27:15.831648+08:00，诊断后继DIAGNOSTICS_COMPLETE_AWAITING_REVIEW，PID3591245 LIVE=False；E0/MASKS COMPLETE，E1_A0/B1及E2_N1-2/N2-0/N2-3五项全部COMPLETE，worker均LIVE=False，新增optimizer更新0。nohup已记录READY N2_COMPLETE_AWAITING_STAGE_PROTOCOL和完整派发/完成序列，无本次故障回报。POST_N2_DIAGNOSTICS_SCREEN True True对应N5问题触发=True、N3问题触发=True，不是两种训练方法有效。N2原科学gate、诊断数值/原件尚待上传回读；不可称已独立验收或确认贡献。

按[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)→[索引](experiments/rebuild_v1/INDEX.md)读取。权威仍为66322/remote_sensing_frequency的rebuild-v1-protocol-20260915。

E0读取已有预测完成，掩码准备完成；E1两worker分别436.28/441.19秒，E2三worker430.03/431.00/427.27秒，五任务实测均约7.1–7.4分钟。E1/E2三个派发波次从约23:05至23:27完成（起始按progress elapsed推算），新增60次tile推理/0训练。CPU E0最后进度23:05:12.250016，缺少CPU开始记录，不能据此推算E0总时长或原N2完成时间。

当前应上传原N2六组记录及诊断E0/E1/E2记录，再复核原计数/绑定/gate并分析问题。已补齐N2上传器对controller_repair_*/repair_bootstrap_*轻量日志、脚本及manifest的收集，不修改原86b6科学快照、9b196a2修复或883fccc诊断快照。具体终端命令见[下一步](current/NEXT_EXPERIMENT.md)。不上新训练队列、不重启已完成任务。

两个问题筛选均触发是值得分析的开发信号；须先看效应大小、两tile一致性、类别/对象分母和混杂。若E1缺口成立优先完整冻结N5四组；若有独立区域问题再考虑N3五组，N4仍等待更新暴露证据。T预留规则不提前评价，13组是条件上限，不自动全跑，不以诊断问题门槛替代N2科学gate。

C/N1原件已验收十组20份summary；C2正确掩码KL与N1-3多深度入口固定gate失败，A2/B3固定gate失败，去留不变。[C/N1结果](experiments/POST_C_N1_RESULTS_20261005.md)、[A/B结果](experiments/POST_D30_AB_RESULTS_20261004.md)。D30部分完整矩阵仍待补。

研究阶段仍为可行性探索；主线RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复旁支。Potsdam fit12/Val2=3_11、5_10，native512/stride256、NoBoundary fg5为主、Full为诊断；单seed42开发证据。只用GPU0/1、nohup、全部产物留zzx对应目录；无SSH、无Test6/independent final、无追加种子、无失败配方自动追训，F/N6保持跳过。

[诊断冻结执行协议](protocols/POST_N2_DIAGNOSTICS_EXECUTION_20261005.md)；[本次完成观测](../records/research_post_n2_diagnostics_20261005T131434_3591073/completion_observation_20261006.json)。
