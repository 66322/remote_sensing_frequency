# 当前状态：诊断验收完成，九组代码READY_NOT_REGISTERED

## 2026-10-07 08:41：N3双卡实际训练已确认

最后服务器只读查询（用户终端）：QUERY_OBSERVED=2026-10-07T08:41:47.885238+08:00，queue LAST_OBSERVED=2026-10-07T08:41:46.005396+08:00，RUNNING_N3_S1，controller PID694658 LIVE=True。GPU0 N3-0 PID694733 LIVE=True，training360/8000，progress08:41:42.634794、1.324986秒/步、训练剩2.811914h；GPU1 N3-1 PID694739 LIVE=True，training360/8000，progress08:41:43.547025、1.328100秒/步、训练剩2.818524h。两worker各加载12/12训练tile，峰值分配约36.79/36.80GB。N3-2/3/4与S1-0/1/2/3七项PENDING；0/9作业COMPLETE。日志确认两个START，无本次故障回报，没有精度或机制gate结果。

原目录research_post_n3_s1_20261007T083203_694293、执行0e22438a7131a0a1f28098e675c3367d40236398保持，不重新登记或重启。CPU准备已完成与登记前检查成功由RUNNING/派发执行链推断；没有单独preparation/check日志原件回读。记录见records/research_post_n3_s1_20261007T083203_694293/user_reported_running_20261007T084147.json。此前仅登记/进度未查询为带时间历史。

当前两组纯训练剩约2h49m，不含4000/8000验证及fixed/selected/U评价。假定后续步速相同，GPU0共五组（当前+四组）、GPU1共四组（当前+三组），训练本身最长lane剩约14.59h；这不是整队ETA，未测后续条件区域/S1及完整评价耗时。九组完整粗范围仍23—34h，从08:32登记参照约2026-10-08 07:30—18:30，非保证，首个完整作业后校准。不能把loss或360步可运行当方法有效。

下一步继续既有nohup队列，按需只读新目录status及日志；失败时保留worker与目录、明确诊断/接管，不自动重试/追加seed/别族。仅GPU0/1，zzx对应目录，无SSH/Test6/independent final/held4或重复资源审计。


## 2026-10-07：九组服务器登记已回报

用户终端返回N3_S1_QUEUE_REGISTERED：目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_n3_s1_20261007T083203_694293，controller PID694658，TRAINING_JOBS=9、NEW_STEPS=72000、GPU=0,1；日志nohup_20261007T083216182460.log。目录08:32:03与日志08:32:16.182460是命名时间标记，不是queue observed_at。登记前同包CPU检查成功返回由执行链推断，尚未单收服务器检查日志。当前REGISTERED_PROGRESS_NOT_YET_QUERIED：未收到controller/worker存活、CPU准备状态、首步或完成回报，不能写为两卡训练已确认。此前READY_NOT_REGISTERED为发布时历史状态。

下一步只读新目录code/scripts/status_post_n3_s1.py与nohup/preparation日志；不再次enqueue、不重启旧N5/N2/cross。记录见records/research_post_n3_s1_20261007T083203_694293/registration_observation.json。估时23—34h仍为规划范围；只有实际启动/首个完整作业回报后校准，不能从登记PID推断精度结果或实时运行。


最后服务器查询：2026-10-07T07:38:05.617099+08:00；queue最后更新2026-10-07T01:08:32.994625+08:00，CROSS_DIAGNOSTICS_COMPLETE_AWAITING_REVIEW。三个E4作业COMPLETE、查询时controller/worker LIVE=False，新增训练0。此后只收到GitHub上传，没有新服务器运行观测。

原件f60491fc1091eb7d272e081e821d9e6397aa9c82已收，独立复算PASS：352载荷路径/大小全匹配，238 JSON载荷及manifest回读，4128矩阵/1168 joint、192 case、576预测索引、106源码索引绑定。没有GPU复跑或服务器大数组/权重本体重新求SHA；3个继承plan JSON仅代码manifest索引，A负控制/C首batch/旧E2 parity为上传元数据验收。[结果报告](../experiments/POST_N5_CROSS_RESULTS_20261007.md)。

N3边界问题与S1 RGB条件特征问题通过，R1 output问题未过。S1收益仅在C=0条件下RGB：N1-2/N2-0/N2-3 +1.307603/+0.577591/+0.595287pp，两tile正；DSM未过，不写双向贡献。N5后边界伤害差约14—15pp且分母足够，E3标准化仍有RGB高DSM变化压力；均不能挽救N5固定配方。

研究阶段可行性探索；主线RGB–DSM条件互补与退化/缺失分割，恢复旁支。用户已授权按规划执行：接续N3五组+S1四组，R1跳过，N4/R2不激活。既有N5/N2/C/N1/A/B去留保持，不调预算/窗口/seed救失败，不因最新问题screen承诺论文创新。

| 阶段 | 状态 | 下一步 |
|---|---|---|
| N5四组 | 原件已验收，固定混合gate失败 | 不重训/换候选救门槛 |
| N2六组/E0/E1/E2 | 完成验收，N2原关系gate失败 | 保留原去留 |
| E3/E4/N5边界 | 原件已收，独立审计PASS | N3/S1问题筛选成立，R1不成立 |
| N3五组/S1四组 | 已登记九组，controller/worker实际进度待查询 | 用户终端启动幂等新队列 |
| N4/R2/其他预约 | 不激活 | 不自动填时长 |

[九组冻结协议](../protocols/POST_N3_S1_EXECUTION_20261007.md)和训练包已实现，CPU17项/11执行Python文件语法PASS（本地合成专家/数据，不是H100科学结果）；服务器登记前同包再验。发布时为READY_NOT_REGISTERED；本次登记PID已收，首步仍待查询，不增加完成数量。

下一步用户终端从本次发布提交取scripts/enqueue_post_n3_s1.py执行--root与--commit。先查原队列/锁、校验已完成cross绑定与固定N1-2完整state；幂等返回已有本类目录，绝不重复登记。CPU准备后nohup自动跑九组，按GPU0/1交替每lane FIFO，N3-4与S1-0可异卡并行，无跨族参数继承。每组新8000/batch16/seed42，72000新增更新，预估23—34h粗范围，首组完整完成后校准。

记录新目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_n3_s1_<timestamp>_<pid>；代码快照/日志/cache/temporary/checkpoint/预测/原矩阵都在对应目录。只GPU0/1，两H10080GB；用户终端无SSH，无重复资源审计。CPU6h/每job12h正有限超时，技术失败停止后续派发，不自动重试。完成N3_S1_COMPLETE_AWAITING_REVIEW后显式轻量上传、GitHub复算；不自动派发别族。

Potsdam fit12/Val2=3_11、5_10，native512/stride256，NoBoundary fg5主/Full诊断，seed42开发证据。沿原三状态4000/8000选模、selected32/fixed22条件，另评冻结U两方向，不读T/H/L新规则、Test6/independent final/held4。工程回退、精度保护、开发机制及独立泛化分别报告。

