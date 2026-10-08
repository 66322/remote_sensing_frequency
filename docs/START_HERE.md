# 共享入口：N3/S1已验收，下一轮仅GPU0

按[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)→[索引](experiments/rebuild_v1/INDEX.md)读取。GitHub 66322/remote_sensing_frequency / rebuild-v1-protocol-20260915为共享权威。

最后服务器查询（用户终端）：2026-10-08T22:11:10.555448+08:00；queue最后观测2026-10-08T06:37:48.607436+08:00，N3_S1_COMPLETE_AWAITING_REVIEW。九组全部COMPLETE/8000，查询时controller/worker LIVE=False。本次只做规划，没有新的服务器运行观测。

[已验收结果](experiments/POST_N3_S1_RESULTS_20261008.md)：N3当前区域配方增量不足；S1-3 RGB局部U +4.102pp，但DSM无稳定收益、aux_shift8/3_11 −0.392pp违反保护。旧gate不改判，单向线索不自动升级双向贡献。验收范围及限制见结果报告。

[下一轮规划](protocols/POST_S1_SUPPORT_GPU0_PLAN_20261008.md)：D0/D1零训练诊断→10组缺失支持×参数隔离配对训练→6条件压力评价，首轮约33—57h；DSM镜像4组仅条件储备。方案未实现、未登记、未启动，不增加已完成实验数。主线仍RGB–DSM条件互补与退化/缺失分割，恢复旁支。

用户2026-10-08最新指令：本轮只能物理GPU0，覆盖诊断、测试、推理、训练及恢复，physical_gpus=[0]、CUDA_VISIBLE_DEVICES=0，单worker串行；GPU1不得使用。旧记录中的GPU0/1仅为历史。服务器由用户终端执行，无SSH；nohup，全部记录/快照/缓存/临时文件在zzx对应新实验目录。无Test6/independent final/held4、失败配方重跑、追加seed或重复资源审计。
