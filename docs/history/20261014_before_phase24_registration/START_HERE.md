# 共享入口：Phase2.4登记期IPC修复待服务器核验（2026-10-14）

当前状态：**IPC_PATH_FIX_READY_AWAITING_SERVER_REGISTRATION_CHECKS**。用户回传失败登记目录research_phase24_protected_20261014T185408_2127460：18项通过、两项AF_UNIX路径错误，无launch.json，0正式推理/训练；不是正在跑的队列。修复已落实，尚无替换目录或真实Linux/CUDA通过证据。

先读[研究决定](current/RESEARCH_DECISION.md)、[交接](current/HANDOFF.md)、[状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)，再读[IPC修复及单次显式技术替换](protocols/PHASE_24_IPC_PATH_FIX_20261014.md)、[修复审计](../records/phase24_ipc_path_fix_20261014/fix_audit.json)、[原执行协议](protocols/PHASE_24_EXECUTION_20261014.md)、[科学门禁](protocols/PHASE_24_DIAGNOSIS_AND_CONDITIONAL_HEADS_20261014.md)。

下一动作：用户运行修复提交的enqueue_phase24.py，显式指定--replace-ipc-path-bug-directory为已观测失败目录。保留旧记录、严格验证0更新登记错误、单次marker防重复、新目录先跑全部26项Linux检查；再做双卡真实smoke，任何失败hold。不要热改/删除旧目录或直接重启controller。

科学任务不变：GPU0/1、≥24h可续，无硬截止；D0–D3、T0及按门禁进入T1/T2/T3，最多4小头32k，0新专家/追加训练seed。抽象socket只在内核命名，不创建/tmp或文件socket；其他临时/记录仍在zzx对应目录，无整轮大缓存。

主线RGB–DSM条件互补与退化/缺失分割，恢复旁支；无SSH、Test6/held4/final及自动配方重试。Phase2完成/旧35910文件退役仍是已验收旧证据，不重启旧队列/清理。[修复前入口归档](history/20261014_before_phase24_ipc_fix/START_HERE.md)。
