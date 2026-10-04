# 当前状态与证据接收

最后服务器观测：2026-10-04T08:41:43.586227+08:00，Post-D30为CONTROLLER_INTERRUPTED，控制器2698383已退出；A0—A5六项COMPLETE，B1—B6/C0—C5待运行，F0—F3有条件。无活跃worker是该时刻的观测，不代表此刻状态。A评价修复已成功，无新增优化器更新；随后A阶段汇总因缺少model导入路径退出。第二次修复2a15ef163c3df7e96ee52c81cb677ebdb1305935已发布并通过本地6项回归，但尚无服务器启动回报。

| 范围 | 最后确认状态 | 证据情况 |
|---|---|---|
| D23/D24/D25/D26 | 完成并分析 | 轻量原件和离线计数复核已在GitHub；D24 Pair无效结论已纠正保留 |
| D27原/修复 | 原step0失败；修复10/10完成 | 原失败不是科学负结果；修复四机制gate均False |
| D28 | 七模型评价完成 | 无新训练；共同受损假设未过门槛，原D29未激活 |
| D30 | 2026-10-04T00:47:08.030508+08:00 COMPLETE 6/6 | 214eb158a59cf8248910ba5e46492189d3a6f953上传156紧凑文件；梯度原件已到，全部逐tile原矩阵未到 |
| Post-D30 | 上述08:41观测6/18主体完成 | A原生结果待收；B/C待续跑；F待B3，第二次恢复未收到执行证据 |

原Post科学执行01ec8dee82f7e272f6a650aaf9f3e619a0e7c516；第一次评价恢复9df2bf44a03955a0db43de1538aff1c91bfae33d；第二次汇总路径修复2a15ef163c3df7e96ee52c81cb677ebdb1305935。原plan/code不覆盖；完成A不重训/不重评价，恢复仅重做阶段汇总并接B/C。

服务器由用户在终端操作，无可用SSH。根目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro；只用物理GPU0/1，两张H10080GB，RAM/磁盘充足。长任务nohup；记录、临时、缓存、执行快照均在/home/jovyan/zzx对应实验目录。当前协议seed42、8000步、物理batch16、无累积。不重复资源审计、容量探针、单模态训练或自动追加多seed。Test6/独立final禁止访问；Val2重复开发，不称独立确认。

[实验总索引](../experiments/rebuild_v1/INDEX.md)、[机读registry](../../records/rebuild_v1_experiment_registry.json)、[整理报告](../experiments/COMPLETED_EXPERIMENTS_HANDOFF_20261004.md)。未知新状态先查询，不据旧PID或GPU空闲自行猜测。
