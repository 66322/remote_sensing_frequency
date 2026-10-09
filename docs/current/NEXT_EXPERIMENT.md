# 下一步：继续P3评价→P0/P1→E，然后上传并独立验收

最后服务器只读查询（用户终端）：QUERY_OBSERVED=2026-10-09T21:31:11.112511+08:00；queue LAST_OBSERVED=21:31:07.216349，RUNNING_P3，controller PID1890742 LIVE=True，仅GPU0。CPU=COMPLETE、D1 COMPLETE（0更新，约43分01秒）；P6/P7/P8/P9/P4/P5/P2七组COMPLETE/8000，worker LIVE=False。P3 PID2437737 LIVE=True、8000/8000，fixed8000阶段，正在3_11/aux_down4评价，本轮主比较仍固定8000。P0/P1和E PENDING；Q=RESERVED_NOT_AUTOMATIC。没有本次故障回报，尚无科学分数/屏幕门槛/轻量原件验收，不能用loss或完成状态判有效。

继续已有队列，只读同目录code/scripts/status_post_s1_support.py和nohup日志；下一步P3完整验收→P0→P1→E→独立汇总。到SUPPORT_COMPLETE_AWAITING_REVIEW后，用code/scripts/upload_post_s1_support_records.py --root ROOT --directory DIR显式上传轻量原件，再独立复算D1/U、八格因素、P8/P9/R0、保护底线与E。完成/失败都保留原目录，不重启已完成P。Q只有D1固定DSM信号及P7/U/E均过才标资格，还需冻结方向协议，不自动训练。

截至21:25的条件估时：还需约10—14h，参照约2026-10-10 07:25—11:25（Asia/Shanghai），非保证。六冻结完整worker实测约1h56m—2h31m，P2共享更新完整worker3h57m53s；P3已训练完但完整评价剩余未测，另两共享组预计各约4h，E仍按1.5—4h规划及汇总开销估算。不是只用remaining_train_hours=0推断整队已完，也不含Q四组。

执行2c5e7d6f383cfe454415d4e106179930264f1141、目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_s1_support_20261008T234921_1890161、controller1890742、nohup_20261008T234938791083.log保持，不重复enqueue或重启旧队列。十P各new8000/seed42/固定S1-0 state、fixed8000主比较，P7为事前指定候选；本次只是带时间进度，不更改科学协议或去留。

本轮ordinary32/fixed22＋两方向U、E六条件，保存逐tile/逐类int64 6×6 CM、joint原计数及checkpoint/源码/input/mask绑定。P7须RGB_U对S1-0≥2pp，对P6/P8/P9各≥.3pp且两tile正，对R0≥−.2pp；clean/fullmissing保护−.1pp、primary最差tile−.2pp、DSM_U−.1pp。E全部保护并在两个clean-DSM新形状≥.5pp/两tile正。固定8000；不后验换候选或改门槛，精确保护只是工程构造，E非独立测试集。

本轮所有训练/推理/恢复只用物理GPU0，CUDA_VISIBLE_DEVICES=0、单worker FIFO。nohup，源码/temporary/cache/记录/预测/权重/轻量上传在zzx对应目录；服务器用户终端执行，无SSH，无GPU1/Test6/independent final/held4/追加seed、失败自动重试或重复资源审计。

可行性探索；主线仍RGB–DSM条件互补与退化/缺失分割，任务恢复旁支，参数隔离与局部支持是本轮待验证交叉问题。旧N3区域配方关闭；S1 RGB局部U+4.102047pp但aux_shift8/3_11−0.391546pp保护失败，旧gate=False，不升级单向线索为双向贡献。N5/N2/C旧去留保持，R1/N4/R2不自动激活。

## 2026-10-09：用户授权运行中完整记录快照并分析

最新查询21:31:11（queue21:31:07）RUNNING_P3、controller LIVE，七P完整，P3在8000步fixed8000评价3_11/aux_down4；P0/P1/E未启动。用户要求先上传并分析已完成作业。[完整作业快照入口及分析口径](../protocols/POST_S1_COMPLETED_SNAPSHOT_ANALYSIS_20261009.md)已实现，6项stdlib回归/help通过；原科学快照不改，队列继续，尚无上传提交或精度原件回报。下一步用户从本次发布commit提取scripts/upload_post_s1_completed_records.py到本实验zzx目录下独立bootstrap并运行，返回COMPLETED_GITHUB_COMMIT后离线复算。

先分析D0/D1、P7对S1-0/P6/P8/P9/R0与保护，未齐共享八格/E不能判全族/最终gate通过；P3只有完整complete后才纳入，不按8000步直接上传。工具冻结COMPLETE名单、跳过RUNNING目录，独立上传worktree，不暂停/重启/启GPU。只GPU0，Q仍储备。
