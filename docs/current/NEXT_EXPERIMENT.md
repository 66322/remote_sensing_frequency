# 下一步：用户登记Phase2.4固定执行快照（2026-10-14）

**IMPLEMENTED_CPU_CHECKED_AWAITING_SERVER_SMOKE**。用户已要求具体执行；[执行包](../protocols/PHASE_24_EXECUTION_20261014.md)与CPU检查完成，服务器尚未登记/启动，无新运行ID。

1. 用户在/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro fetch本分支，用包含本执行包的40位SHA取scripts/enqueue_phase24.py执行。唯一登记入口先查询research_phase24_protected_*、原队列锁/完成标记、GPU0/1；存在队列则查询原状态，忙卡则不登记。不要直接重跑controller或原Phase2。
2. 自动核验原输入/源代码/权重/mask、有效CPU/RAM；Linux全部CPU检查、两卡backward-only梯度和各6个原CM桥接smoke先通过。CPU并发候选16/24/32在同匿名RAM case上基准选择。失败进入hold，保留现场，不自动替换或救配方。
3. 自动D0–D3及T0；T1/T2/T3严格条件派发。资源窗口GPU0/1≥24h可续，无硬截止；最多4小头32k，0专家/额外训练seed。4k轨迹与固定8k共用前向评价，不挑年龄/seed。
4. 用新目录code/scripts/status_phase24.py --directory <D>只读查询：最后观测、控制/worker存活、GPU窗口、CPUcase、当前阶段ETA；不能从旧日志或GPU0%判断完成。
5. PHASE24_COMPLETE_AWAITING_REVIEW并确认进程退出后，用户运行code/scripts/upload_phase24.py --directory <D>；只上传白名单轻量原件归档，fetch回读每个分块。不要无交互后台等待GitHub密码；断线后同入口继续，不重复科学任务。
6. 接收实际运行ID/计数/资源峰值，验原件及门禁后更新研究决定/结果/交接。校准充分停止复杂分支；无部署信号仅停止当前观察/决策类。8k小头评审后再定长期价值，不提前删除原专家。

原大缓存已退役，新实验只读共享RAM和有界匿名包，最后消费者即回收。计数、配置、源参数/代码/轨迹/必要模型留证；自动删除仅该新目录的rolling resume及评价完成后的4k临时pth，先复算整数summary。无Test6/held4/final、SSH、自动重试或扩大旧文件删除范围。[原下一步归档](../history/20261014_before_phase24_execution/NEXT_EXPERIMENT.md)。
