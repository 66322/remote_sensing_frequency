# 当前交接：Phase2.4替换已登记，查询新目录（2026-10-14）

## 已观测登记与下一动作
**REGISTERED_LAUNCH_OBSERVED_AWAITING_STATUS**。用户回传新目录：
/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase24_protected_20261014T193915_2149100
执行5a84f0eacabe5d6f1c7ed1638e6a9291c58e151f；PID2149894；nohup_20261014T193920570637.log。最后观测为用户回传登记输出：目录时间2026-10-14 19:39:15，日志文件名时间19:39:20.570637；尚未接收此后的status、CPU日志原件或真实GPU smoke结果，不表述为实时持续运行。

固定登记脚本只有全部26项Linux CPU测试成功且无skip、创建controller Popen后才打印REGISTERED，因此运输路径修复通过这一级准入；CPU日志/registration_cpu_checks.json原件未逐byte接收，双卡真实CUDA/12 CM桥接未验收，不把此记录写成正式case完成或持续存活。

唯一下一动作：用户用上述新目录code/scripts/status_phase24.py --directory <D>及tail新nohup日志只读查询，回传当前最后观测/存活/阶段。不要再次登记或替换，不重启controller。原185408_2127460是保留的失败快照，不再用于进度。

## 科学预算与资源
D0–D3、T0 clean8k必做、校准不足且probe保护通过才派T1/T2各8k、再条件T3 8k；最多4头32k，0新专家/训练seed，GPU0/1≥24h可续无硬截止。原B1/B3及L=False不改，4k轨迹/8k固定主端点不挑年龄。输入核验及双卡真实smoke通过前不派正式任务。[执行](../protocols/PHASE_24_EXECUTION_20261014.md)、[科学门禁](../protocols/PHASE_24_DIAGNOSIS_AND_CONDITIONAL_HEADS_20261014.md)。

原9.792GB输入只读共享；每卡最多2匿名包、<1GiB clean缓存、mask LRU8；样本≤1GiB、CPU16/24/32按实际配额/同case基准选择。抽象AF_UNIX通信不创建文件，不改TMPDIR到/tmp；其他记录/临时仍在zzx对应新目录。不恢复旧整轮缓存，评价后计数复算及临时pth退役，必要端点暂留待审。

## 工程事故与旧研究边界
原research_phase24_protected_20261014T185408_2127460执行15f：18项通过、两项AF_UNIX路径失败，无launch、0正式推理/训练。此次用户显式单次技术替换，原seal/code/log保留、marker防重复；不属于已训练配方重试。[修复](../protocols/PHASE_24_IPC_PATH_FIX_20261014.md)、[登记](../../records/phase24_registration_20261014/observation_193920.json)。

主线RGB–DSM条件互补与退化/缺失分割，恢复旁支；两重复Val2/seed42仅开发证据。Phase2完成及35910文件退役是此前已验收记录；原缓存不能再假定在线，不重复旧队列/清理。工程准入成功不改变C/L、研究路线或新科学结论。

服务器由用户执行，无SSH、Test6/held4/final或自动失败重跑。当前等待状态查询，成功结束后用户显式upload_phase24.py、白名单归档/回读，重要门禁与交接继续同分支同步。[登记前交接](../history/20261014_before_phase24_registration/HANDOFF.md)。
