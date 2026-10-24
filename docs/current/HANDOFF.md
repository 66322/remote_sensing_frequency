# 当前交接：已收到F0 seed42 clean指标，等待完整条件面板（2026-10-24）

最后服务器观测2026-10-24 22:49:33+08:00：M2 RUNNING，控制器报告完成17/108训练作业、失败/阻断0，19个作业有progress；GPU0 F0_s17_DShuffle为16600/32000，GPU1 F0_s17_DEntropy为11420/32000。两控制器及两GPU worker存活，合并WAIT_M2。当前完整故障面板counted_cases=0、evaluation=null，尚无M2阶段summary。这是最后观测，不是实时状态或完整科学验收。 本轮仅读取用户回执并更新共享记录，无新服务器操作。[原始回执与解释](../experiments/PHASE3_M2_PROGRESS_20261024T224933.md).

用户已明确把[启动复盘](../experiments/PHASE3_STARTUP_POSTMORTEM_20261024.md)写为跨对话长期要求。先读[根AGENTS](../../AGENTS.md)、[稳定入口](NEW_CHAT_HANDOFF.md)、[执行约定](../protocols/EXECUTION_CONTRACT.md)与[启动交付/故障控制](../protocols/STARTUP_DELIVERY_AND_FAILURE_CONTROL.md)。真实包/分包布局及目标路径必须验；已有未变绑定复用，不因换对话、补规则或观测过期重新启动/审计。

当前目录：

- M2：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m2_revision_20261024T092814_2738345
- 合并：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_combined_revision_20261024T092814_2738345

科学来源M2 ac325cdbb403ebb95b5eb0acbf17fffa5441dcfd、合并e65c6cb0830985461b3cd30e2f43158dd3d858cb；运行修订752d3835a18a15a04d83b1dcc1841bff98bf0b07、包路径25b124a0cf69ececb6841b55ed90b19fae5b9a08分别绑定。全局records/phase3_engineering_restart_20261024_once.json为CONTROLLERS_LAUNCHED。原两失败目录及修复前史保留，不删回执/锁或重建目录绕过重复保护。

当前接续动作：继续已有队列，由用户按需只读运行records/phase3_engineering_restart_package_752d3835a18a15a04d83b1dcc1841bff98bf0b07/scripts/status_phase3_engineering_restart.py --tail 40；按[只读进度与结果指南](../protocols/PHASE3_PROGRESS_AND_RESULTS.md)查看已有文件，继续后续轨迹与首折36作业齐全后的完整面板评价；最终阶段汇总须等108及计数完整。出现新错误读取首个原栈并停止后续派发，不自动重跑；不再bootstrap、repair --apply、改环境或重启。T1/T3是M2内层教师。xFormers禁用警告未阻断实际更新，瞬时GPU利用率不用于改预算；count_workers32为配置、22:49采样cpu_tasks0，ps异常ELAPSED不用作时长。

工程已有目标检查与首更证据：CPU真实模型/权重、memfd传递及路径补丁8项、原M2 16项、合并11项；没有因此验收后续真实训练、完整评估或全部轻量原件。结束须额外核验752d runtime和25b124补丁材料、全部端点/原始整数计数/轨迹及轻量上传。旧失败CPU/磁盘残留未现场全审计。

研究阶段仍为可行性/机制筛选；主线RGB–DSM条件互补与退化/缺失分割、恢复旁支。独立地图维护是助手优先候选，未确认为主线或自动入队。M2→J→R→T→V最多228作业/5088000更新；B/C不开放，3DCD/P³两catalog未就绪时后段WAIT_PUBLIC_DATA。GPU0/1、用户执行无SSH、有界内存、test封存、失败不自动重跑/加seed均保持。

[范围/耗时/遗留](../experiments/PHASE3_QUEUE_SCOPE_ETA_AND_REMAINS_20261024.md)；[数据与保存规则](../experiments/PHASE3_DATA_AND_ARTIFACT_STORAGE_20261024.md)。同速72–75小时仅为纯训练情景；后段publication不等于已自动上传GitHub。原始资料大部分仍在服务器。前一交接见[归档](../history/HANDOFF_20261024_BEFORE_M2_17_COMPLETED.md)。

本次0.348–0.350秒/步是加权对照实测速率，剩余1.5/2.0小时只指两在途作业纯优化；不沿用RGB教师同速情景承诺整队列完工。counted_cases不含年龄轨迹计数，17完成尚不足任一外折36作业，当前无阶段汇总符合流程。

2026-10-24 23:39:19+08:00已收到[首张实际中间指标](../experiments/PHASE3_M2_INTERIM_F0_S42_20261024T233919.md)：F0 seed42七个DSM臂32k、四tile齐全，D0 nb fg5=62.9713%，DF=62.3730%（-0.5983pp），六个改动臂均低于D0；DF也低于DShuffle约0.51pp。属于局部clean单模态负向证据，无条件补救/融合结论；G3保护对象是融合，不能把DSM单模态差值套其门槛。full-GT是同中央内缩计分域的全标签诊断，不是全tile。17行eligible不等于全M2 G0；seed17两行32k缺计数不等于失败。汇总器624194105b3b018bb1e1e66d80cada2a405e7758目标读取成功，未重算推理或更新训练。23:39仅指标读取，最后进程/GPU观测仍22:49:33。继续冻结队列，等待原条件补救/损伤、融合及保护面板；不改配方、选年龄、加seed或提前判路线。前一交接见[归档](../history/HANDOFF_20261024_BEFORE_FIRST_INTERIM_METRICS.md)。


2026-10-25用户再次纠正非必要多seed和GPU低利用率：[核对复盘](../experiments/PHASE3_PLANNING_POLICY_AUDIT_20261025.md)确认9月29日规范已存在，但根/稳定入口未接入，M2三seed未充分说明为何两个不足，训练GPU分段吞吐也未闭环。已将[规划规范](../protocols/EXPERIMENT_PLANNING_RULES.md)接入必读链并补准备表。探索默认单seed，必要重复通常先42/17，第三须具体理由；现M2仍108/三seed，未改/停/重启队列或完成加速。当前低利用率是用户报告，完整运行观测仍10月24日22:49、指标读取23:39。若后续决定缩减或加速，先定向读现有进度、保留全部证据，修订依赖/门禁与执行版本，不按分数裁种子或热改。上一版见[归档](../history/HANDOFF_20261025_BEFORE_SEED_THROUGHPUT_POLICY_AUDIT.md)。
