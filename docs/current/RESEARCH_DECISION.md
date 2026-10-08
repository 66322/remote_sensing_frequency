# 研究决定：保留S1单向线索，规划缺失支持与参数隔离

前置[完整结果](../experiments/POST_N3_S1_RESULTS_20261008.md)已独立验收，原件38d205591abe00179bebfb36a17595d4d7b75f47，验收提交4163107e55bc560a8ba83784e3759caa3a4a299b。N3固定候选相对局部−0.000078pp、相对网格+0.001937pp，关闭该区域配方的增量承诺。S1-3 RGB局部U对S1-0 +4.102047pp，两tile正；DSM −0.023201pp且tile异号；aux_shift8/3_11 −0.391546pp违反原−0.2pp保护线。两旧gate维持False，S1是单向收益与退化代价的开发线索。

研究阶段仍为可行性探索，主线RGB–DSM条件互补与退化/缺失分割，恢复旁支。Potsdam fit12/Val2=3_11、5_10、native512/stride256、NoBoundary fg5主/Full诊断、seed42；两Val tile反复开发，不宣称独立泛化/显著性。N5/N2/C旧配方去留保持，R1/N4/R2不自动激活。

新[Post-S1单卡规划](../protocols/POST_S1_SUPPORT_GPU0_PLAN_20261008.md)已获用户“按上述规划进行”授权，[执行协议](../protocols/POST_S1_SUPPORT_EXECUTION_20261008.md)和独立单卡包CPU检查通过，REGISTERED_PROGRESS_NOT_YET_QUERIED：D0复用预测＋D1权重/策略诊断→P十组（2×2×2配对＋2机制控制）→E六压力条件；Q四组仅条件储备。约33—57h首轮单卡预算，首个隔离/共享作业后校准，无科学总时间上限。新代码/单卡入口已建立，服务器登记已回报，PID1890742、目录research_post_s1_support_20261008T234921_1890161；存活与GPU进度尚未查询；Q仅条件储备，不运行旧双卡enqueue。

P十组统一旧S1-0 selected8000完整state、新8000步、seed42、原数据/增强/损失、固定8000主比较（4000仅诊断），共80000新更新。比较共享/冻结基座、掩码/保留上下文、全域/局部修正；P7固定为冻结基座＋保留上下文＋局部修正，P8支持分层空间打乱、P9仅logit/mask校准。D0同时建立零训练双模型拼接R0。冻结局部保护是构造属性，贡献必须超越P6/P8/P9/R0并通过未参与训练的六合成压力条件；具体门槛见规划。

代码已实现的旧S1完整可用输入下四种B/C策略退化为同图，present-but-bad退化仍mask=true。因此代价可能来自训练后参数变化；这是源码支持的推断，D1先核同权重不变性，不能提前写为已验证因果。

决定来源：用户本次授权规划下一阶段并将后续资源限制到GPU0。助手提出十组新设计，未成为已验证方法/最终论文贡献。未采纳N3后验换候选、增加seed/预算、忽略S1最差条件、自动启用旧储备族。Q镜像DSM仅在固定诊断DSM信号和P7的U/E同时通过后另冻结具体协议，证据不足跳过。

用户2026-10-08最新指令：本轮只能物理GPU0，覆盖诊断、测试、推理、训练及恢复，physical_gpus=[0]、CUDA_VISIBLE_DEVICES=0，单worker串行；GPU1不得使用。旧记录中的GPU0/1仅为历史。服务器由用户终端执行，无SSH；nohup，全部记录/快照/缓存/临时文件在zzx对应新实验目录。无Test6/independent final/held4、失败配方重跑、追加seed或重复资源审计。

最后服务器查询（用户终端）：2026-10-08T22:11:10.555448+08:00；queue最后观测2026-10-08T06:37:48.607436+08:00，N3_S1_COMPLETE_AWAITING_REVIEW。九组全部COMPLETE/8000，查询时controller/worker LIVE=False。本次只做规划，没有新的服务器运行观测。


最新服务器登记回报（用户终端，2026-10-08）：SUPPORT_QUEUE_REGISTERED，目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_s1_support_20261008T234921_1890161，controller PID1890742，GPU=0 ONLY，TRAINING_JOBS=10、NEW_STEPS=80000、Q_RESERVED_NOT_RUNNABLE=4；日志nohup_20261008T234938791083.log。目录23:49:21及日志23:49:38.791083为命名时间标记，不是queue observed_at。当前REGISTERED_PROGRESS_NOT_YET_QUERIED，尚无controller/worker存活、D0/D1进度、CUDA首步或完成回报，不能写为训练已确认。

原队列登记前检查回报：最后观测2026-10-08T06:37:48.607436+08:00，COMPLETE RELEASED。登记前CPU检查成功返回由执行入口链推断，服务器cpu_checks.log尚未单独接收；本地22项/12Python语法检查保持其合成CPU范围。

下一步只读已有目录code/scripts/status_post_s1_support.py、nohup_20261008T234938791083.log及可选preparation.log，获取queue最后观测/存活/阶段/worker首步。不要再次enqueue、重启原N3/S1或创建第二条队列；完成/失败后显式upload_post_s1_support_records.py，轻量原件回读复算后评科学去留。CPU准备阶段GPU空闲不能直接判故障。
