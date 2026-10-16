# 当前状态：Phase2.4登记失败，IPC修复待服务器核验（2026-10-14）

|项目|证据/状态|
|---|---|
|原失败登记|research_phase24_protected_20261014T185408_2127460；15fdfa4c|
|用户回传CPU检查|20项18通过、两项AF_UNIX path too long；无launch.json|
|正式新实验|控制器/正式GPU推理/训练均未启动，0更新|
|IPC修复包|IPC_PATH_FIX_READY_AWAITING_SERVER_REGISTRATION_CHECKS|
|本地修复检查|26项23通过、3项真实Linux检查待执行；14文件编译|
|替换登记|尚未执行/没有新目录观测；用户需显式技术替换参数|

18:54:08是原目录登记时间；失败结束时间未提供。上述为用户回传的最后证据，不是实时服务器查询。[用户摘录](../../records/phase24_ipc_path_fix_20261014/user_cpu_log_excerpt.txt)、[修复协议](../protocols/PHASE_24_IPC_PATH_FIX_20261014.md)、[修复审计](../../records/phase24_ipc_path_fix_20261014/fix_audit.json)。

科学口径/预算不变：GPU0/1 ≥24h可续、最多4头32k、0新专家/seed、原C/L与B1/B3不变。抽象socket不创建文件，其他记录/临时仍在zzx新目录；保留旧失败快照。新26检查及双卡真实smoke未通过前不派正式任务。

旧Phase2最后完成2026-10-14T00:39:03.210695+08:00，核心4训练48k、上传dc335e0d；C=True、L=False。[结果](../experiments/PHASE_2_RESULTS_20261014.md)。旧35910文件清理回执12:13:25.974504+08:00，普通大cache已退役，不重复清理/重启。

主线RGB–DSM互补与退化/缺失分割、恢复旁支；反复Val2/seed42为开发证据。无SSH、Test6/held4/final或自动配方重试。[修复前状态](../history/20261014_before_phase24_ipc_fix/PROJECT_STATUS.md)。
