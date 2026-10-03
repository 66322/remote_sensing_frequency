# START HERE：D26九组完成，D26/D27最终原件待上传

权威分支rebuild-v1-protocol-20260915，更新2026-10-03。读[研究决定](current/RESEARCH_DECISION.md)→[交接](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)。

D26最后服务器观测2026-10-03T04:04:45.239849+08:00 COMPLETE9/9；上传因原文超过512MiB失败，尚未取得最终指标。D27查询未执行，最新已知仍10-02 23:32 WAITING_D26，不按时间推定完成。[观测与修复](experiments/D26_COMPLETE_UPLOAD_FIX_20261003.md)。先重传原件，不重启队列/训练。

大型JSON采用无损文本信封，读取时先解码并核对原大小/SHA；服务器原件保留，小JSON直接可读。两轮代码/选模/gate不改。GPU0/1 H10080GB、RAM/磁盘充足、nohup、zzx对应目录为持续约定，不重问资源或重做预算审计。Test6禁读，开发Val2/暴露held4不作独立final。

[假设与近期论文复核](experiments/ASSUMPTIONS_AND_RESEARCH_OPPORTUNITIES_20261003.md)为助手研究建议，不是已新增运行。先收齐19组结果，再决定下一实验。主问题保留双方信息、退化/缺失；强基线及旧失败结论保持，无新确认性贡献。
