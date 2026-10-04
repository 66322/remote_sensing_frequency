# 当前状态与证据接收

最后服务器观测：2026-10-04T17:21:47.568226+08:00（用户终端查询回传），Post-D30为RUNNING，控制器2720259 LIVE=True，主体12/18完成：A0—A5、B1—B6全部COMPLETE；C0在GPU0训练3760/8000步，C1在GPU1训练3780/8000步，两worker PID_LIVE=True；C2—C5 PENDING，F0—F3仍有条件。原队列已进入C，禁止重复恢复或新建队列。旧08:12日志的model导入错误仅作历史记录。本次仍未收到上传提交，GitHub没有新增A/B原生结果；固定A2/B3门槛尚待原件分析，不能由技术完成判定科学成立。

| 范围 | 最后确认状态 | 证据情况 |
|---|---|---|
| D23/D24/D25/D26 | 完成并分析 | 轻量原件和离线计数复核已在GitHub；D24 Pair无效结论已纠正保留 |
| D27原/修复 | 原step0失败；修复10/10完成 | 原失败不是科学负结果；修复四机制gate均False |
| D28 | 七模型评价完成 | 无新训练；共同受损假设未过门槛，原D29未激活 |
| D30 | 2026-10-04T00:47:08.030508+08:00 COMPLETE 6/6 | 214eb158a59cf8248910ba5e46492189d3a6f953上传156紧凑文件；梯度原件已到，全部逐tile原矩阵未到 |
| Post-D30 | 17:21观测12/18主体完成 | A/B原生结果待收；A/B全完成，C0/C1运行，C2—C5待接续；F待固定B3门槛核验 |

原Post科学执行01ec8dee82f7e272f6a650aaf9f3e619a0e7c516；第一次评价恢复9df2bf44a03955a0db43de1538aff1c91bfae33d；第二次汇总路径修复2a15ef163c3df7e96ee52c81cb677ebdb1305935。原plan/code不覆盖；完成A不重训/不重评价，原队列进入C已观测，禁止再次启动恢复，修复manifest仍待核验。

服务器由用户在终端操作，无可用SSH。根目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro；只用物理GPU0/1，两张H10080GB，RAM/磁盘充足。长任务nohup；记录、临时、缓存、执行快照均在/home/jovyan/zzx对应实验目录。当前协议seed42、8000步、物理batch16、无累积。不重复资源审计、容量探针、单模态训练或自动追加多seed。Test6/独立final禁止访问；Val2重复开发，不称独立确认。

[实验总索引](../experiments/rebuild_v1/INDEX.md)、[机读registry](../../records/rebuild_v1_experiment_registry.json)、[整理报告](../experiments/COMPLETED_EXPERIMENTS_HANDOFF_20261004.md)。未知新状态先查询，不据旧PID或GPU空闲自行猜测。
