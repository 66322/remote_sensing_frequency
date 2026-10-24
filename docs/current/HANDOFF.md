# 当前交接：M2实际训练已确认，按长期规则只读接续（2026-10-24）

最后服务器观测仍为2026-10-24 09:54:39+08:00：M2 RUNNING，输入12/12；GPU0 F0_s42_T3为2600/32000、GPU1 F0_s42_T1为2620/32000，失败0、完成端点0。M2/合并控制器2754693/2754694存活，GPU worker2757402/2757403；合并WAIT_M2为正常依赖等待。不是实时状态；本轮只固化长期规则，没有新的服务器操作或观测。[原始回执与解释](../experiments/PHASE3_REVISION_TRAINING_STARTED_20261024.md)。

用户已明确把[启动复盘](../experiments/PHASE3_STARTUP_POSTMORTEM_20261024.md)写为跨对话长期要求。先读[根AGENTS](../../AGENTS.md)、[稳定入口](NEW_CHAT_HANDOFF.md)、[执行约定](../protocols/EXECUTION_CONTRACT.md)与[启动交付/故障控制](../protocols/STARTUP_DELIVERY_AND_FAILURE_CONTROL.md)。真实包/分包布局及目标路径必须验；已有未变绑定复用，不因换对话、补规则或观测过期重新启动/审计。

当前目录：

- M2：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m2_revision_20261024T092814_2738345
- 合并：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_combined_revision_20261024T092814_2738345

科学来源M2 ac325cdbb403ebb95b5eb0acbf17fffa5441dcfd、合并e65c6cb0830985461b3cd30e2f43158dd3d858cb；运行修订752d3835a18a15a04d83b1dcc1841bff98bf0b07、包路径25b124a0cf69ececb6841b55ed90b19fae5b9a08分别绑定。全局records/phase3_engineering_restart_20261024_once.json为CONTROLLERS_LAUNCHED。原两失败目录及修复前史保留，不删回执/锁或重建目录绕过重复保护。

唯一当前动作：继续已有队列，由用户按需只读运行records/phase3_engineering_restart_package_752d3835a18a15a04d83b1dcc1841bff98bf0b07/scripts/status_phase3_engineering_restart.py --tail 40；按[只读进度与结果指南](../protocols/PHASE3_PROGRESS_AND_RESULTS.md)查看已有文件，等后续轨迹及首个完整32k端点。出现新错误读取首个原栈并停止后续派发，不自动重跑；不再bootstrap、repair --apply、改环境或重启。T1/T3是M2内层教师。xFormers禁用警告未阻断实际更新，瞬时GPU利用率不用于改预算；count_workers32为配置、当时cpu_tasks0，ps异常ELAPSED不用作时长。

工程已有目标检查与首更证据：CPU真实模型/权重、memfd传递及路径补丁8项、原M2 16项、合并11项；没有因此验收后续真实训练、完整评估或全部轻量原件。结束须额外核验752d runtime和25b124补丁材料、全部端点/原始整数计数/轨迹及轻量上传。旧失败CPU/磁盘残留未现场全审计。

研究阶段仍为可行性/机制筛选；主线RGB–DSM条件互补与退化/缺失分割、恢复旁支。独立地图维护是助手优先候选，未确认为主线或自动入队。M2→J→R→T→V最多228作业/5088000更新；B/C不开放，3DCD/P³两catalog未就绪时后段WAIT_PUBLIC_DATA。GPU0/1、用户执行无SSH、有界内存、test封存、失败不自动重跑/加seed均保持。

[范围/耗时/遗留](../experiments/PHASE3_QUEUE_SCOPE_ETA_AND_REMAINS_20261024.md)；[数据与保存规则](../experiments/PHASE3_DATA_AND_ARTIFACT_STORAGE_20261024.md)。同速72–75小时仅为纯训练情景；后段publication不等于已自动上传GitHub。原始资料大部分仍在服务器。前一交接见[归档](../history/HANDOFF_20261024_BEFORE_DURABLE_STARTUP_RULES.md)。
