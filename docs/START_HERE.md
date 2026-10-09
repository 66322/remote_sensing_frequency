# 共享入口：Post-S1七组已分析，P7未过R0门槛

按[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)→[索引](experiments/rebuild_v1/INDEX.md)读取；GitHub同分支为共享权威。

已独立接收原件77d3970fdfcf3d72524f8c31ff412110196161a6，[阶段结果](experiments/POST_S1_PARTIAL_RESULTS_20261009.md)：固定P7 RGB_U=83.575357%，对S1-0 +2.562756pp、P6 +1.759726、P8 +1.952962、P9 +2.207993，均两tile正；ordinary十primary、clean/全缺失与DSM_U增量0，保护通过。但R0=85.001650%，P7−R0=−1.426292pp、两tile负，违反事前−0.2pp必要底线，P7当前具体配方门槛失败。固定S1-0 DSM方向D1信号−0.050601pp、tile异号，Q必要条件也失败。E未收到，完整final gate未评齐；后续E无法推翻已经失败的必要条件。

最新已接收服务器快照：捕获2026-10-09T21:43:00.478470+08:00，queue最后观测21:42:23.635611，RUNNING_P3，controller PID1890742；这是上传时原记录，不是发布时实时查询。CPU/D1完整，P6/P7/P8/P9/P4/P5/P2七组完整；P3 RUNNING，P0/P1/E PENDING，Q条件储备。本次未查询服务器存活，不把原PID/旧进度写成当前实时。

继续既有队列P3→P0/P1→E，不改协议、不重训完成项。剩余共享三格补齐2×2×2配对，E六形状×DSM质量压力条件补适用边界；它们属于原授权范围，不能后验以最高组替换P7或救固定gate。只读原目录code/scripts/status_post_s1_support.py及原nohup日志获取新观测。到SUPPORT_COMPLETE_AWAITING_REVIEW后运行原目录code/scripts/upload_post_s1_support_records.py --root ROOT --directory DIR上传全批轻量原件，再独立验收。Q仍不自动启动，本次必要条件不足，不开启镜像方向或旧R1/N4/R2储备。

可行性探索；主线仍RGB–DSM条件互补与退化/缺失分割，任务驱动恢复旁支。保留局部空间上下文相对匹配控制的正线索及构造保护能力，不自动升级主线/最终论文贡献，也不把P7失败扩大为整个问题无效。Potsdam fit12/Val2 3_11、5_10，native512/stride256、NoBoundary fg5主、Full/6类诊断、seed42；反复开发Val2，不是独立泛化/多seed确认。旧N3/S1、N5/N2/C去留与门槛不改。

科学执行2c5e7d6f383cfe454415d4e106179930264f1141，原目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_s1_support_20261008T234921_1890161，nohup_20261008T234938791083.log，十P各新8000/seed42/固定S1-0 state；P7事前指定，4000仅诊断，固定8000主比较。全后续GPU活动只能物理GPU0/CUDA_VISIBLE_DEVICES=0，单worker FIFO；服务器用户终端，无SSH。所有记录/快照/临时/cache仍在zzx对应目录；无GPU1/Test6/held4/independent final、失败自动重跑、新seed、重复enqueue或资源审计。

[阶段报告](experiments/POST_S1_PARTIAL_RESULTS_20261009.md)、[审计范围](../records/post_s1_partial_offline_audit_20261009/README.md)、[冻结协议](protocols/POST_S1_SUPPORT_EXECUTION_20261008.md)。本次离线分析/发布，没有GPU重跑或服务器队列修改。