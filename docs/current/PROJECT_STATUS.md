# 状态：Post-D30已启动并排队等待D30

最后用户回传为2026-10-04 00:08启动日志（时间取目录名，日志行无独立时间戳）：Post-D30控制器PID2450552已由nohup启动，CPU检查通过，记录`PORTFOLIO_WAITING_D30 RUNNING`，即已排队等待D30。执行commit固定01ec8dee82f7e272f6a650aaf9f3e619a0e7c516，新目录`research_post_d30_mechanisms_20261004T000812_2446364`；所给日志尚无新GPU worker启动。没有/proc直接存活检查或完整queue_status回传，不能把此次日志当作持续实时存活保证。D30在该日志中被间接观测为RUNNING；其最后直接进度仍为10月3日23:17，随后四项完成指标已分析，PR_area/PR_pixel、重放效果及原矩阵待收。

| 阶段 | 最后证据 | 科学状态 |
|---|---|---|
| D26 | 2026-10-03 04:04 COMPLETE9/9 | 已复核，普通融合保留，当前复杂主候选未过gate |
| 原D27 | 2026-10-03 04:12 step0技术失败 | 无效果结论，原目录保留 |
| D27 repair | 2026-10-03 18:22 COMPLETE10/10 | 四科学gate失败 |
| D28 | 2026-10-03 19:27 COMPLETE7/7 | 238原件重算、压力gate失败 |
| D29 | 无启动观测 | 条件不成立，未排队 |
| D30 | 23:17运行观测＋随后四项完成指标 | P小增益、R明显损失，PR_area/PR_pixel等待收；原件未独立重算 |
| Post-D30 A/B/C/F | 2026-10-04 00:08启动日志 | nohup PID2450552；CPU检查通过；WAITING_D30，尚无新GPU训练启动证据 |

主问题仍为RGB外观/语义与DSM高度/几何的双向条件互补及任一模态退化/缺失下的可靠分割。处于论文可行性探索，频率、语义可靠性、专家与共享/私有只是候选解法；任务驱动SR/恢复仍为旁支，没有自动转向或确认性贡献。

[四项结果分析](../experiments/D30_FOUR_ARM_REVIEW_20261003.md)、[执行协议](../protocols/POST_D30_EXECUTION_20261003.md)、[机读计划](../../records/research_post_d30_design_20261003/plan.json)。

只使用物理GPU0/1，两张H10080GB；RAM/磁盘充足，无资源探针。seed42、8000步、batch16无累积、nohup。快照、临时、缓存、日志全部在/home/jovyan/zzx对应实验目录。用户在服务器终端执行，无SSH；Test6与独立final禁读。重复开发Val2不是确认性泛化证据。GitHub本分支为共享权威，大预测/checkpoint本体留服务器并索引。

[历史状态全文](../history/pre_post_D30_execution_20261003/PROJECT_STATUS.md)。

[本次启动观测](../../records/research_post_d30_mechanisms_20261004T000812_2446364/launch_observation_20261004T000812.json)。
