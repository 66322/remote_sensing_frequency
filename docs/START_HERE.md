# 共享入口：诊断已验收，N3/S1九组执行包就绪

## 2026-10-07 08:41：N3双卡实际训练已确认

最后服务器只读查询（用户终端）：QUERY_OBSERVED=2026-10-07T08:41:47.885238+08:00，queue LAST_OBSERVED=2026-10-07T08:41:46.005396+08:00，RUNNING_N3_S1，controller PID694658 LIVE=True。GPU0 N3-0 PID694733 LIVE=True，training360/8000，progress08:41:42.634794、1.324986秒/步、训练剩2.811914h；GPU1 N3-1 PID694739 LIVE=True，training360/8000，progress08:41:43.547025、1.328100秒/步、训练剩2.818524h。两worker各加载12/12训练tile，峰值分配约36.79/36.80GB。N3-2/3/4与S1-0/1/2/3七项PENDING；0/9作业COMPLETE。日志确认两个START，无本次故障回报，没有精度或机制gate结果。

原目录research_post_n3_s1_20261007T083203_694293、执行0e22438a7131a0a1f28098e675c3367d40236398保持，不重新登记或重启。CPU准备已完成与登记前检查成功由RUNNING/派发执行链推断；没有单独preparation/check日志原件回读。记录见records/research_post_n3_s1_20261007T083203_694293/user_reported_running_20261007T084147.json。此前仅登记/进度未查询为带时间历史。

当前两组纯训练剩约2h49m，不含4000/8000验证及fixed/selected/U评价。假定后续步速相同，GPU0共五组（当前+四组）、GPU1共四组（当前+三组），训练本身最长lane剩约14.59h；这不是整队ETA，未测后续条件区域/S1及完整评价耗时。九组完整粗范围仍23—34h，从08:32登记参照约2026-10-08 07:30—18:30，非保证，首个完整作业后校准。不能把loss或360步可运行当方法有效。

下一步继续既有nohup队列，按需只读新目录status及日志；失败时保留worker与目录、明确诊断/接管，不自动重试/追加seed/别族。仅GPU0/1，zzx对应目录，无SSH/Test6/independent final/held4或重复资源审计。


## 2026-10-07：九组服务器登记已回报

用户终端返回N3_S1_QUEUE_REGISTERED：目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_n3_s1_20261007T083203_694293，controller PID694658，TRAINING_JOBS=9、NEW_STEPS=72000、GPU=0,1；日志nohup_20261007T083216182460.log。目录08:32:03与日志08:32:16.182460是命名时间标记，不是queue observed_at。登记前同包CPU检查成功返回由执行链推断，尚未单收服务器检查日志。当前REGISTERED_PROGRESS_NOT_YET_QUERIED：未收到controller/worker存活、CPU准备状态、首步或完成回报，不能写为两卡训练已确认。此前READY_NOT_REGISTERED为发布时历史状态。

下一步只读新目录code/scripts/status_post_n3_s1.py与nohup/preparation日志；不再次enqueue、不重启旧N5/N2/cross。记录见records/research_post_n3_s1_20261007T083203_694293/registration_observation.json。估时23—34h仍为规划范围；只有实际启动/首个完整作业回报后校准，不能从登记PID推断精度结果或实时运行。


按[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)→[索引](experiments/rebuild_v1/INDEX.md)读取。GitHub 66322/remote_sensing_frequency / rebuild-v1-protocol-20260915为共享权威。

最后服务器查询：2026-10-07T07:38:05.617099+08:00；queue最后更新2026-10-07T01:08:32.994625+08:00，CROSS_DIAGNOSTICS_COMPLETE_AWAITING_REVIEW。三个E4作业COMPLETE、查询时controller/worker LIVE=False，新增训练0。此后只收到GitHub上传，没有新服务器运行观测。

已上传诊断f60491f独立复算PASS，N3/S1问题门槛通过、R1失败。[验收报告](experiments/POST_N5_CROSS_RESULTS_20261007.md)。原N5/N2失败去留保持，S1仅RGB、C=0下条件线索，不是双向方法验证。

用户已授权接续N3五组+S1四组；[冻结执行协议](protocols/POST_N3_S1_EXECUTION_20261007.md)、训练包、CPU17项及11执行文件语法通过。发布时READY_NOT_REGISTERED；本次登记PID已收，实际进度待查询。用户终端运行本次发布的enqueue_post_n3_s1.py；先核旧队列、幂等登记，再nohup自动九组，每组新8000，固定N1-2完整state、seed42/batch16。预估23—34小时粗范围，首完整作业校准；不为填满两天追加失败配方/seed。

研究阶段可行性探索；主线RGB–DSM条件互补与退化/缺失分割，恢复旁支。Potsdam fit12/Val2两tile/native512/stride256、NoBoundary fg5主。只GPU0/1、zzx对应新实验目录、用户终端无SSH，无Test6/independent final/held4或重复资源审计。轻量原件完成后同步GitHub并复算。
