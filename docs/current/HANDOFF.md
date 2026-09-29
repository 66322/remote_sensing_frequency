# 当前交接：D21 已归档，吞吐短测已回传

最后带时钟的服务器记录：2026-09-29 18:54:40–18:55:00，GPU0 吞吐短测采样（CSV 未注明时区），测试已结束；没有当前运行状态证据。D21 原48项队列更早于18:23:44 +08:00按预定 STOP 退出，旧记录为 `32/48 INCOMPLETE`，有效双种子范围为 `32/32 COMPLETE`。

[D21结果报告](../experiments/D21_DETAIL_FREQUENCY_RESULTS_20260929.md)记载预设 F2 候选四块增益均未达 +0.2 pp，DSM 完全缺失的四块安全门槛也全部失败；Vaihingen 有逐 tile 负迁移。D21 开发筛选关闭，Test6 和独立 final 均未启用。原运行和归档命令见[历史交接](../history/20260929_before_d21_results/HANDOFF.md)。

后续机制探索默认单种子，针对 DSM 缺失和失败 tile 设匹配对照及冻结门槛。需要新数据或环境时，按[实验准备规则](../protocols/EXPERIMENT_PLANNING_RULES.md)先列明来源、体量、网络和中转准备，再安排训练。

吞吐短测[原始 JSON 与 GPU 采样](../experiments/POST_D21_THROUGHPUT_PROBE_RESULTS_20260929.md)已由用户归档至 `6e45fce`。`16×1` 短测最快，`8×2` 仅慢约2.5%；约55%时间用于准备/传输，整卡采样未显示显存瓶颈。下一步实现[D22结构对齐可靠性草案](../protocols/D22_STRUCTURE_ALIGNED_DSM_RELIABILITY_DRAFT_20260929.md)，核对 R0 锚点与缺失 DSM 精确回退、四组匹配及短时数值稳定性；正式队列尚未启动。
