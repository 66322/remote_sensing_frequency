# START HERE：D26结果已复核，D27接力后十组技术失败

权威分支rebuild-v1-protocol-20260915，更新2026-10-03。读[研究决定](current/RESEARCH_DECISION.md)→[交接](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)。

[完整结果与失败复核](experiments/D26_COMPLETE_D27_FAILURE_REVIEW_20261003.md)：D26最后观测2026-10-03T04:04:45.239849+08:00 COMPLETE9/9，180份主tile矩阵独立重算一致；XSF相对B0 S+0.156829pp未过原+0.2，语义不足，频率有有限线索，双方独有信息门槛失败。关闭当前候选确认路径，不改阈值/追训；保留普通融合强基线和主问题。

D27最后观测2026-10-03T04:12:45.117489+08:00 COMPLETE_WITH_TECHNICAL_FAILURES，0/10，全部首次objective因treatment字段在转GPU时被丢弃失败。接力确实发生，不能写成仍等待/已获得精度结果/研究假设失败。原件f3d2be8已上传；根因已修并补回归。修复未在服务器执行，补跑用新目录，原记录保留，见NEXT。

仅GPU0/1 H10080GB，RAM/磁盘充足，nohup和zzx对应目录持续有效，无资源探针，不重跑D26。GitHub原件与权重/预测服务器索引分开；Test6禁读，开发Val2/暴露held4不作独立final。[假设研究建议](experiments/ASSUMPTIONS_AND_RESEARCH_OPPORTUNITIES_20261003.md)待D27有效结果后决定，尚未排队。
