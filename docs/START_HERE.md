# 共享入口：诊断已验收，N3/S1九组执行包就绪

按[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)→[索引](experiments/rebuild_v1/INDEX.md)读取。GitHub 66322/remote_sensing_frequency / rebuild-v1-protocol-20260915为共享权威。

最后服务器查询：2026-10-07T07:38:05.617099+08:00；queue最后更新2026-10-07T01:08:32.994625+08:00，CROSS_DIAGNOSTICS_COMPLETE_AWAITING_REVIEW。三个E4作业COMPLETE、查询时controller/worker LIVE=False，新增训练0。此后只收到GitHub上传，没有新服务器运行观测。

已上传诊断f60491f独立复算PASS，N3/S1问题门槛通过、R1失败。[验收报告](experiments/POST_N5_CROSS_RESULTS_20261007.md)。原N5/N2失败去留保持，S1仅RGB、C=0下条件线索，不是双向方法验证。

用户已授权接续N3五组+S1四组；[冻结执行协议](protocols/POST_N3_S1_EXECUTION_20261007.md)、训练包、CPU17项及11执行文件语法通过。当前READY_NOT_REGISTERED，尚无新服务器PID/进度。用户终端运行本次发布的enqueue_post_n3_s1.py；先核旧队列、幂等登记，再nohup自动九组，每组新8000，固定N1-2完整state、seed42/batch16。预估23—34小时粗范围，首完整作业校准；不为填满两天追加失败配方/seed。

研究阶段可行性探索；主线RGB–DSM条件互补与退化/缺失分割，恢复旁支。Potsdam fit12/Val2两tile/native512/stride256、NoBoundary fg5主。只GPU0/1、zzx对应新实验目录、用户终端无SSH，无Test6/independent final/held4或重复资源审计。轻量原件完成后同步GitHub并复算。
