# 当前交接：多方向一天以上实验已规划，尚未实施

最后带时钟的服务器记录：2026-09-29 18:54:40–18:55:00，GPU0 吞吐短测采样（CSV 未注明时区），测试已结束；没有当前运行状态证据。D21 原48项队列更早于18:23:44 +08:00按预定 STOP 退出，旧记录为 `32/48 INCOMPLETE`，有效双种子范围为 `32/32 COMPLETE`。

[D21结果报告](../experiments/D21_DETAIL_FREQUENCY_RESULTS_20260929.md)记载预设 F2 候选四块增益均未达 +0.2 pp，DSM 完全缺失的四块安全门槛也全部失败；Vaihingen 有逐 tile 负迁移。D21 开发筛选关闭，Test6 和独立 final 均未启用。原运行和归档命令见[历史交接](../history/20260929_before_d21_results/HANDOFF.md)。

用户最新要求：先规划至少一天、可多方向及交叉问题、非必要不多种子。[新计划](../protocols/POST_D21_MULTIDIRECTION_DAY_PLAN_20260929.md)定义42项主训练及8项备用，全部seed42：表征适配、学习型DSM残差、真实LR恢复/分割和恢复×DSM交叉。主计划576k新更新；目标24–48h，新增模型先实测，不能承诺按F2耗时达到该范围。当前只完成规划，无新训练代码或启动命令。

吞吐短测[原始 JSON 与 GPU 采样](../experiments/POST_D21_THROUGHPUT_PROBE_RESULTS_20260929.md)归档于 `6e45fce`。下一步落实新计划的代码/对照，再测冻结、解冻及恢复前端的真实训练链；特别检查恢复前端收到分割梯度。D9B固定边缘分数的负结果使旧D22固定Sobel门不再是主方案。B使用学习型RGB条件残差，缺失回退只作为工程不变量。主计划无需新下载；发现缺项按[准备规则](../protocols/EXPERIMENT_PLANNING_RULES.md)先说明。上版交接见[历史](../history/20260929_before_multidirection_plan/HANDOFF.md)。
