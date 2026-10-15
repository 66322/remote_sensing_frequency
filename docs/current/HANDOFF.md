# 当前交接：Phase3-M1执行包就绪，等待服务器启动回执（2026-10-15）

Phase3-M1已按用户要求落实执行包，尚未取得服务器启动回执。仅使用本篇遥感RGB/DSM/标签，GPU0/1，固定16k、batch16；11个新主训练，最多2个条件反证，总上限13个新训练208k更新。旧M00/42在绑定合格时复用，Test6/held4/final不读，点云论文不进入本轮。

双卡共享就绪队列，空闲卡可以领取另一seed任务。GPU到CPU交接只等内存接收，不等计数完成；RGB故障前向跨所有DSM对照共享。Fit训练RAM在全部训练消费者结束后分进程释放，条件预测匿名RAM在最后计数消费者结束后关闭，成功作业的滚动优化器在端点与主计数核验后退役。GPU无后续任务时先退出，CPU继续收尾；所有自有进程退出后清理runtime cache/temporary。负结果、失败恢复状态、必要16k权重和充分整数证据保留。

[执行与清理协议](../protocols/PHASE3_M1_EXECUTION_20261015.md)；[科学设计](../protocols/PHASE3_M1_DESIGN_20261015.md)；[包清单](../../configs/phase3_m1_execution_manifest.json)；[本机检查记录](../../records/phase3_m1_implementation_review_20261015.json)。

## 直接接续

固定执行包已经实现，不再从设计阶段重新讨论是否编写。服务器启动需由用户执行；收到启动日志前状态为EXECUTION_PACKAGE_READY_NOT_LAUNCHED。bootstrap继承已完成Phase2.4本地冻结code，下载并校验本包白名单，不完整克隆大归档仓库。实际新run在/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m1_<真实时间>_<PID>；不能编造目录、PID、GPU运行中或完成时刻。

启动后从launch.json、queue_status.json和progress_gpu*.json读取真实状态；旧PID和旧tmux/Git排错已收尾。失败不自动重跑；独立任务继续，失败/跳过和清理回执齐全归档。计算不等待Git认证，完成后独立前台上传紧凑原件。

Phase2.4原件76ae973b已完整验收，calibrated/probe=False，T0完成8k、T1/T2/T3未派发。旧结果不改，新实验不视为旧门禁翻案。
