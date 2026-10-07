# 共享入口：诊断已验收，N3/S1九组执行包就绪

## 2026-10-07：九组服务器登记已回报

用户终端返回N3_S1_QUEUE_REGISTERED：目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_n3_s1_20261007T083203_694293，controller PID694658，TRAINING_JOBS=9、NEW_STEPS=72000、GPU=0,1；日志nohup_20261007T083216182460.log。目录08:32:03与日志08:32:16.182460是命名时间标记，不是queue observed_at。登记前同包CPU检查成功返回由执行链推断，尚未单收服务器检查日志。当前REGISTERED_PROGRESS_NOT_YET_QUERIED：未收到controller/worker存活、CPU准备状态、首步或完成回报，不能写为两卡训练已确认。此前READY_NOT_REGISTERED为发布时历史状态。

下一步只读新目录code/scripts/status_post_n3_s1.py与nohup/preparation日志；不再次enqueue、不重启旧N5/N2/cross。记录见records/research_post_n3_s1_20261007T083203_694293/registration_observation.json。估时23—34h仍为规划范围；只有实际启动/首个完整作业回报后校准，不能从登记PID推断精度结果或实时运行。


按[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)→[索引](experiments/rebuild_v1/INDEX.md)读取。GitHub 66322/remote_sensing_frequency / rebuild-v1-protocol-20260915为共享权威。

最后服务器查询：2026-10-07T07:38:05.617099+08:00；queue最后更新2026-10-07T01:08:32.994625+08:00，CROSS_DIAGNOSTICS_COMPLETE_AWAITING_REVIEW。三个E4作业COMPLETE、查询时controller/worker LIVE=False，新增训练0。此后只收到GitHub上传，没有新服务器运行观测。

已上传诊断f60491f独立复算PASS，N3/S1问题门槛通过、R1失败。[验收报告](experiments/POST_N5_CROSS_RESULTS_20261007.md)。原N5/N2失败去留保持，S1仅RGB、C=0下条件线索，不是双向方法验证。

用户已授权接续N3五组+S1四组；[冻结执行协议](protocols/POST_N3_S1_EXECUTION_20261007.md)、训练包、CPU17项及11执行文件语法通过。发布时READY_NOT_REGISTERED；本次登记PID已收，实际进度待查询。用户终端运行本次发布的enqueue_post_n3_s1.py；先核旧队列、幂等登记，再nohup自动九组，每组新8000，固定N1-2完整state、seed42/batch16。预估23—34小时粗范围，首完整作业校准；不为填满两天追加失败配方/seed。

研究阶段可行性探索；主线RGB–DSM条件互补与退化/缺失分割，恢复旁支。Potsdam fit12/Val2两tile/native512/stride256、NoBoundary fg5主。只GPU0/1、zzx对应新实验目录、用户终端无SSH，无Test6/independent final/held4或重复资源审计。轻量原件完成后同步GitHub并复算。
