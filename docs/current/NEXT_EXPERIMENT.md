# 下一步：显式替换已知零更新IPC登记事故（2026-10-14）

状态**IPC_PATH_FIX_READY_AWAITING_SERVER_REGISTRATION_CHECKS**。原失败目录 research_phase24_protected_20261014T185408_2127460 的18项检查通过，两项socket路径失败，无launch/科学任务。新修复尚未服务器核验，不直接运行旧controller或删除旧目录。

1. 用户fetch本分支，使用修复提交的40位SHA取scripts/enqueue_phase24.py；加--replace-ipc-path-bug-directory，值为上述完整原目录。只接受已证明零更新的特定IPC失败；保留原seal/code/log，用新独立快照。重复同命令只查询marker指向目录，不重复派发。
2. 新目录全部26项Linux CPU检查必须通过无skip；之后才自动启动控制器、双卡梯度和各6个原CM桥接。任何异常hold并保留，不自动再替换或救科学配方。
3. 成功后D0–D3/T0和条件T1/T2/T3自动执行；原预算/输入/精度/训练流不变，GPU0/1 ≥24h可续、最多4头32k、0新专家/seed。不要因工程失败调整科研门禁。
4. 保存新打印的目录、日志和状态命令；查询其status_phase24.py。原失败目录没有运行进度，不能继续用旧D查新队列或从GPU0%判断完成。
5. 完成并进程退出后，用户运行新目录upload_phase24.py；白名单含technical_replacement索引，轻量归档并回读。接收实际原件、门禁和资源峰值后更新共享结论/交接。

[具体修复与准入守卫](../protocols/PHASE_24_IPC_PATH_FIX_20261014.md)、[执行协议](../protocols/PHASE_24_EXECUTION_20261014.md)、[科学门禁](../protocols/PHASE_24_DIAGNOSIS_AND_CONDITIONAL_HEADS_20261014.md)。主线、存储即用即回收、重复Val2开发证据边界保持；无SSH、Test6/held4/final及自动失败配方重试。[修复前下一步](../history/20261014_before_phase24_ipc_fix/NEXT_EXPERIMENT.md)。
