# 当前交接：多方向实验代码已准备，等待服务器预检与短测

最后带时钟的服务器记录：2026-09-29 18:54:40–18:55:00，GPU0 吞吐短测采样（CSV 未注明时区），测试已结束；没有当前运行状态证据。D21 原48项队列更早于18:23:44 +08:00按预定 STOP 退出，旧记录为 `32/48 INCOMPLETE`，有效双种子范围为 `32/32 COMPLETE`。

[D21结果报告](../experiments/D21_DETAIL_FREQUENCY_RESULTS_20260929.md)记载预设 F2 候选四块增益均未达 +0.2 pp，DSM 完全缺失的四块安全门槛也全部失败；Vaihingen 有逐 tile 负迁移。D21 开发筛选关闭，Test6 和独立 final 均未启用。原运行和归档命令见[历史交接](../history/20260929_before_d21_results/HANDOFF.md)。

用户已要求按[新计划](../protocols/POST_D21_MULTIDIRECTION_DAY_PLAN_20260929.md)执行。现已加入 A/B/C/D/E 模型、50项清单驱动的单任务训练/逐 tile 评价、物理 GPU0/1 队列、实际微批吞吐短测、整数计数复核与[服务器执行说明](../protocols/POST_D21_DAY_EXECUTION_20260929.md)。本地 CPU 模型梯度/回退检查通过；**服务器还未预检、短测或启动新训练**。主计划42项，备用8项，全部seed42。不能把代码存在误写为实验已验证。

吞吐旧短测[原始 JSON 与 GPU 采样](../experiments/POST_D21_THROUGHPUT_PROBE_RESULTS_20260929.md)归档于 `6e45fce`，不能用于新模型 ETA。下一步服务器拉取本分支，依次运行 `--prepare-only`、`--profile-only`；核对新 `scope.json` 的预计工时/资源后，`--launch` 自动完成冻结范围。缺失资产先说明，不自动下载。D9B固定边缘分数的负结果使旧D22固定Sobel门不再是主方案；B缺失回退只作为工程不变量。上版交接见[历史](../history/20260929_before_multidirection_plan/HANDOFF.md)。
