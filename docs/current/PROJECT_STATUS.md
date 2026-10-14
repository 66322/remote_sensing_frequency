# 当前状态：Phase2.4替换登记成功，当前运行状态待查（2026-10-14）

|项目|最后证据|
|---|---|
|新目录|research_phase24_protected_20261014T193915_2149100|
|执行/PID|5a84f0ea / 2149894，Popen已创建|
|Linux CPU准入|26项全通过且无skip，由固定登记脚本控制流和用户REGISTERED输出推断|
|真实GPU/正式任务|输入完成、CUDA smoke、原CM桥接、case/训练进度尚未观测|
|原失败快照|185408_2127460保留，显式技术替换完成登记；不是当前进度目录|

最后观测为用户回传登记输出：目录时间2026-10-14 19:39:15，日志文件名时间19:39:20.570637；尚未接收此后的status、CPU日志原件或真实GPU smoke结果，不表述为实时持续运行。 [登记信息](../../records/phase24_registration_20261014/observation_193920.json)。当前状态**REGISTERED_LAUNCH_OBSERVED_AWAITING_STATUS**，不推断控制器持续存活。

下一步只读查询新目录status与nohup日志；不再执行登记/替换，不直接重启。GPU0/1、最多4小头32k、0新专家/训练seed，≥24h可续，无硬截止；实际进入哪些头仍按科学门禁。原C/L及B1/B3不改。

原Phase2最后完成2026-10-14T00:39:03.210695+08:00；旧35910文件退役回执12:13:25.974504+08:00，普通cache已离线。[旧结果](../experiments/PHASE_2_RESULTS_20261014.md)。主线/开发证据边界不变，无SSH、Test6/held4/final、自动配方重试。[登记前状态](../history/20261014_before_phase24_registration/PROJECT_STATUS.md)。
