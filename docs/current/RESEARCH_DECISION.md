# 研究决定：保留S1单向线索，规划缺失支持与参数隔离

前置[完整结果](../experiments/POST_N3_S1_RESULTS_20261008.md)已独立验收，原件38d205591abe00179bebfb36a17595d4d7b75f47，验收提交4163107e55bc560a8ba83784e3759caa3a4a299b。N3固定候选相对局部−0.000078pp、相对网格+0.001937pp，关闭该区域配方的增量承诺。S1-3 RGB局部U对S1-0 +4.102047pp，两tile正；DSM −0.023201pp且tile异号；aux_shift8/3_11 −0.391546pp违反原−0.2pp保护线。两旧gate维持False，S1是单向收益与退化代价的开发线索。

研究阶段仍为可行性探索，主线RGB–DSM条件互补与退化/缺失分割，恢复旁支。Potsdam fit12/Val2=3_11、5_10、native512/stride256、NoBoundary fg5主/Full诊断、seed42；两Val tile反复开发，不宣称独立泛化/显著性。N5/N2/C旧配方去留保持，R1/N4/R2不自动激活。

新[Post-S1单卡规划](../protocols/POST_S1_SUPPORT_GPU0_PLAN_20261008.md)已获用户“按上述规划进行”授权，[执行协议](../protocols/POST_S1_SUPPORT_EXECUTION_20261008.md)和独立单卡包CPU检查通过，RUNNING_P3（2026-10-09T21:25最后观测）：D0复用预测＋D1权重/策略诊断→P十组（2×2×2配对＋2机制控制）→E六压力条件；Q四组仅条件储备。约33—57h首轮单卡预算，首个隔离/共享作业后校准，无科学总时间上限。新代码/单卡入口已建立，服务器登记已回报，PID1890742、目录research_post_s1_support_20261008T234921_1890161；控制器LIVE=True、CPU/D1完成、七P完成，P3评价8000步，P0/P1/E待运行；Q仅条件储备，不运行旧双卡enqueue。

P十组统一旧S1-0 selected8000完整state、新8000步、seed42、原数据/增强/损失、固定8000主比较（4000仅诊断），共80000新更新。比较共享/冻结基座、掩码/保留上下文、全域/局部修正；P7固定为冻结基座＋保留上下文＋局部修正，P8支持分层空间打乱、P9仅logit/mask校准。D0同时建立零训练双模型拼接R0。冻结局部保护是构造属性，贡献必须超越P6/P8/P9/R0并通过未参与训练的六合成压力条件；具体门槛见规划。

代码已实现的旧S1完整可用输入下四种B/C策略退化为同图，present-but-bad退化仍mask=true。因此代价可能来自训练后参数变化；这是源码支持的推断，D1先核同权重不变性，不能提前写为已验证因果。

决定来源：用户本次授权规划下一阶段并将后续资源限制到GPU0。助手提出十组新设计，未成为已验证方法/最终论文贡献。未采纳N3后验换候选、增加seed/预算、忽略S1最差条件、自动启用旧储备族。Q镜像DSM仅在固定诊断DSM信号和P7的U/E同时通过后另冻结具体协议，证据不足跳过。

用户2026-10-08最新指令：本轮只能物理GPU0，覆盖诊断、测试、推理、训练及恢复，physical_gpus=[0]、CUDA_VISIBLE_DEVICES=0，单worker串行；GPU1不得使用。旧记录中的GPU0/1仅为历史。服务器由用户终端执行，无SSH；nohup，全部记录/快照/缓存/临时文件在zzx对应新实验目录。无Test6/independent final/held4、失败配方重跑、追加seed或重复资源审计。

最后服务器只读查询（用户终端）：QUERY_OBSERVED=2026-10-09T21:25:10.899578+08:00；queue LAST_OBSERVED=21:25:10.879724，RUNNING_P3，controller PID1890742 LIVE=True，仅GPU0。CPU=COMPLETE、D1 COMPLETE（0更新，约43分01秒）；P6/P7/P8/P9/P4/P5/P2七组COMPLETE/8000，worker LIVE=False。P3 PID2437737 LIVE=True、8000/8000，checkpoint_selection阶段，正在3_11/dsm_missing的验证/评价；该标签继承旧进度命名，本轮主比较仍固定8000。P0/P1和E PENDING；Q=RESERVED_NOT_AUTOMATIC。没有本次故障回报，尚无科学分数/屏幕门槛/轻量原件验收，不能用loss或完成状态判有效。

截至21:25的条件估时：还需约10—14h，参照约2026-10-10 07:25—11:25（Asia/Shanghai），非保证。六冻结完整worker实测约1h56m—2h31m，P2共享更新完整worker3h57m53s；P3已训练完但完整评价剩余未测，另两共享组预计各约4h，E仍按1.5—4h规划及汇总开销估算。不是只用remaining_train_hours=0推断整队已完，也不含Q四组。

继续已有队列，只读同目录code/scripts/status_post_s1_support.py和nohup日志；下一步P3完整验收→P0→P1→E→独立汇总。到SUPPORT_COMPLETE_AWAITING_REVIEW后，用code/scripts/upload_post_s1_support_records.py --root ROOT --directory DIR显式上传轻量原件，再独立复算D1/U、八格因素、P8/P9/R0、保护底线与E。完成/失败都保留原目录，不重启已完成P。Q只有D1固定DSM信号及P7/U/E均过才标资格，还需冻结方向协议，不自动训练。
