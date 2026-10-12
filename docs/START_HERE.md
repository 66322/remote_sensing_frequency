# 共享入口：Phase1.5双卡执行包就绪（2026-10-12）

权威分支66322/remote_sensing_frequency / rebuild-v1-protocol-20260915。

2026-10-12用户“按上述规划进行”并“继续”，已落实Phase1.5独立执行包。**READY_NOT_REGISTERED**：本地20项合成CPU检查与13新Python语法通过，尚无服务器登记/PID或真实权重/CUDA结果。GPU0/1、100工作批次、1540唯一逻辑case（两S1 clean缓存复用，按最多1538新tile推理计）；0训练/0优化器更新，24–48h预留且无24h总截止。

启动入口enqueue_phase15.py幂等检查旧完成队列/锁，继承immutable源码→CPU检查→准备→GPU0真实smoke(ID1/tile3_11)→GPU1同case一致性→自动技术验收全PASS→双卡全量→五项汇总。任一技术失败HOLD且停止拥有的children，不自动retry或加训练。用户终端执行、无SSH，全部记录/缓存/临时产物在/home/jovyan/zzx新目录。

旧两轮最后上传观测：Post-T 2026-10-12T11:03:22.917566+08:00，8/8 COMPLETE、PAIRED_SCREEN=False；Structured 2026-10-12T16:32:44.762198+08:00，42/42 COMPLETE、NO_SUPPORT_THIS_PROTOCOL。不是当前服务器实时查询。R16−H16+0.348562pp局部门槛通过，总失败来自5/6 E−R0底线；独立预算未支持盲目续训，但R16自身后8k仍+0.618217pp。S1主PE+0.122522pp/CI跨0，RGB-only+3.119077pp；旧gate不改。

主线RGB–DSM双向条件互补与退化/缺失，恢复旁支。五项诊断齐全再选方法，routing/context都是条件候选，不自动训练、不扩mask/seed、不加载Test6/held4/final。

先读[新交接](current/NEW_CHAT_HANDOFF_20261011.md)→[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一实验](current/NEXT_EXPERIMENT.md)→[执行协议](protocols/PHASE_1_5_EXECUTION_20261012.md)→[设计](protocols/PHASE_1_5_RECOVERABILITY_20261012.md)与原件。唯一立即下一步是用户终端执行本次固定commit的bootstrap；新队列不存在运行回报。
