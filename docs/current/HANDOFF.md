# 当前交接：执行包已发布，唯一下一步服务器登记（2026-10-12）

2026-10-12用户“按上述规划进行”并“继续”，已落实Phase1.5独立执行包。**READY_NOT_REGISTERED**：本地20项合成CPU检查与13新Python语法通过，尚无服务器登记/PID或真实权重/CUDA结果。GPU0/1、100工作批次、1540唯一逻辑case（两S1 clean缓存复用，按最多1538新tile推理计）；0训练/0优化器更新，24–48h预留且无24h总截止。

启动入口enqueue_phase15.py幂等检查旧完成队列/锁，继承immutable源码→CPU检查→准备→GPU0真实smoke(ID1/tile3_11)→GPU1同case一致性→自动技术验收全PASS→双卡全量→五项汇总。任一技术失败HOLD且停止拥有的children，不自动retry或加训练。用户终端执行、无SSH，全部记录/缓存/临时产物在/home/jovyan/zzx新目录。

旧两轮最后上传观测：Post-T 2026-10-12T11:03:22.917566+08:00，8/8 COMPLETE、PAIRED_SCREEN=False；Structured 2026-10-12T16:32:44.762198+08:00，42/42 COMPLETE、NO_SUPPORT_THIS_PROTOCOL。不是当前服务器实时查询。R16−H16+0.348562pp局部门槛通过，总失败来自5/6 E−R0底线；独立预算未支持盲目续训，但R16自身后8k仍+0.618217pp。S1主PE+0.122522pp/CI跨0，RGB-only+3.119077pp；旧gate不改。

主线RGB–DSM双向条件互补与退化/缺失保持，恢复旁支。本轮仅RGB局部缺失诊断，不能预先认定路由或边界修复有效。可靠性/routing从默认方法降为条件候选，源自既有D27/D30失败和oracle/可识别性未决。

下一：用户从本次发布commit提取enqueue_phase15.py并运行，保存PHASE15_REGISTERED目录与日志。无需另外确认双卡/时长；暂不处理释放单卡。无需重新登记原26机制队列或Post-T/Structured队列。

技术smoke由控制器自动验收并接续全量；科学判断等完整轻量原件上传后复核。此为用户执行授权后的流程落实，前版“smoke回传人工验收后才登记全量”的操作被本执行协议取代，科学gate不变。

必须继承A同DSM-clean对照、B PE=NA/固定M5支持、DSM等形状双射、D完整NB raw gate与legacy限制、ECI非正分母NA、zero-init不是训练后保护保证。GT/真实mask分箱仅机制描述，部署可学习性不得自动判定。

[执行协议](../protocols/PHASE_1_5_EXECUTION_20261012.md)、[完整设计](../protocols/PHASE_1_5_RECOVERABILITY_20261012.md)、[双卡规划](../protocols/PHASE_1_5_TWO_GPU_PLAN_20261012.md)、[CPU验证记录](../../records/phase15_execution_design_20261012/validation.json)。
