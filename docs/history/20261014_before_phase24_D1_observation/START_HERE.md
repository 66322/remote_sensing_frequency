# 共享入口：Phase2.4技术替换已登记，等待当前状态（2026-10-14）

当前状态：**REGISTERED_LAUNCH_OBSERVED_AWAITING_STATUS**。新目录research_phase24_protected_20261014T193915_2149100，执行5a84f0ea，登记输出PID=2149894。根据固定登记脚本控制流，26项Linux CPU检查已全通过无skip；已创建控制器进程，真实GPU smoke/当前存活仍未观测。最后观测为用户回传登记输出：目录时间2026-10-14 19:39:15，日志文件名时间19:39:20.570637；尚未接收此后的status、CPU日志原件或真实GPU smoke结果，不表述为实时持续运行。

先读[研究决定](current/RESEARCH_DECISION.md)、[交接](current/HANDOFF.md)、[状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)，再读[登记观测](../records/phase24_registration_20261014/observation_193920.json)、[执行协议](protocols/PHASE_24_EXECUTION_20261014.md)、[IPC修复](protocols/PHASE_24_IPC_PATH_FIX_20261014.md)、[科学门禁](protocols/PHASE_24_DIAGNOSIS_AND_CONDITIONAL_HEADS_20261014.md)。

下一动作是用户只读查询新目录status_phase24.py和nohup日志，不再登记/替换，不沿用185408旧失败目录查进度。原失败快照保留。无SSH；正式任务仍须输入核验和两卡真实smoke通过。

主线RGB–DSM互补与退化/缺失分割、恢复旁支不变。GPU0/1、≥24h可续、最多4小头32k、0新专家/训练seed、原B1/B3门禁不改；无Test6/held4/final、自动失败重试或整轮磁盘cache。[登记前入口](history/20261014_before_phase24_registration/START_HERE.md)。
