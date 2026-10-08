# 项目状态：Post-S1执行包CPU通过，登记已回报，进度待查询

最新服务器登记回报（用户终端，2026-10-08）：SUPPORT_QUEUE_REGISTERED，目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_s1_support_20261008T234921_1890161，controller PID1890742，GPU=0 ONLY，TRAINING_JOBS=10、NEW_STEPS=80000、Q_RESERVED_NOT_RUNNABLE=4；日志nohup_20261008T234938791083.log。目录23:49:21及日志23:49:38.791083为命名时间标记，不是queue observed_at。当前REGISTERED_PROGRESS_NOT_YET_QUERIED，尚无controller/worker存活、D0/D1进度、CUDA首步或完成回报，不能写为训练已确认。

原队列登记前检查回报：最后观测2026-10-08T06:37:48.607436+08:00，COMPLETE RELEASED。登记前CPU检查成功返回由执行入口链推断，服务器cpu_checks.log尚未单独接收；本地22项/12Python语法检查保持其合成CPU范围。

用户已授权按GPU0[规划](../protocols/POST_S1_SUPPORT_GPU0_PLAN_20261008.md)实施。[冻结执行包](../protocols/POST_S1_SUPPORT_EXECUTION_20261008.md)已实现，REGISTERED_PROGRESS_NOT_YET_QUERIED：D0复用/拼接→D1四权重四策略→P十组→E六条件→独立汇总。P7固定候选、S1-0基座SHA、新8000×10/seed42、fixed8000主比较、原科学门槛保持。CPU合成检查22项及12Python语法通过；没有真实服务器权重/backbone/GPU复跑，登记前同包CPU检查已成功返回（执行链推断，原log待收）。

|阶段|状态|预算/边界|
|---|---|---|
|旧N3五组/S1四组|完成并独立验收|原gateFalse，报告见N3/S1结果|
|D0|实现、已登记，进度待查询|CPU复用，0更新|
|D1|实现、服务器待执行|48新tile推理，0更新|
|P0—P9|实现、服务器待执行|10×8000更新，GPU0 FIFO|
|E|实现、服务器待执行|6条件×12模型×2tile，0更新|
|Q镜像DSM|条件储备、无可运行协议|最多4组，资格不自动启动|

可行性探索，主线仍RGB–DSM条件互补与退化/缺失分割，任务恢复旁支。N3当前区域增量不足，S1 RGB局部+4.102047pp但aux_shift8/3_11−0.391546pp保护失败，旧gate维持False；本轮研究缺失支持与参数隔离，不自动升级单向收益为双向贡献。N5/N2/C旧去留保持，R1/N4/R2不激活。

仅物理GPU0，physical_gpus=[0]、CUDA_VISIBLE_DEVICES=0、单worker FIFO，所有诊断/训练/推理/恢复均不得使用GPU1。nohup、全部记录/快照/cache/temporary/上传worktree在zzx对应新目录；用户终端执行，无SSH，无Test6/独立final/held4、追加seed或失败配方自动重跑。旧双卡入口不适用于本轮。

本次工程检查范围为合成CPU数据/专家/模拟进程、真实入口导入/help与汇总流程，真实backbone/权重/GPU尚未检查。前置[已验收结果](../experiments/POST_N3_S1_RESULTS_20261008.md)的原件范围/限制保持，不因执行包就绪增加完成实验数。
