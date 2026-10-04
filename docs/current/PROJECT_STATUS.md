# 状态：D30已完成；Post-D30技术停止

最新用户回传A0/A1 worker日志（未附新的服务器观测时间；日志会话始于2026-10-04T08:12:25，不能以此代替当前时刻）：两项RUNNING，均打印PORTFOLIO_REPAIR_EVAL_ONLY optimizer_updates=0 reused_rows=20；均已完成evaluation 3_11 dsm_present_zero及dsm_present_shift_half，并推进至evaluation 5_10 rgb_local_q1。原诊断条件阻塞已越过，补评价真实推进；尚未收到complete.json/COMPLETE观测，因此不宣称两项完整完成或最终权重不变校验已通过。上一带时间的队列观测为2026-10-04T08:14:26.221138+08:00，控制器2698383、A0/GPU0 worker2698740、A1/GPU1 worker2698743存活。其余A→B→C→条件F顺序保持，不重启。

最后服务器观测：D30在2026-10-04T00:47:08.030508+08:00为COMPLETE，六项全部完成。Post-D30在2026-10-04T06:04:04.397991+08:00为COMPLETE_WITH_TECHNICAL_FAILURES；原控制器2450552已退出（Z、LIVE=False），无活跃worker。A0—A5均训练至8000步，均因评价条件`dsm_present_zero`未被处理而失败；0/18正式完成，B/C未启动，F仍待条件。不能据此评价A机制效果。原执行commit为01ec8dee82f7e272f6a650aaf9f3e619a0e7c516，原目录为`research_post_d30_mechanisms_20261004T000812_2446364`。该失败观测为06:04历史状态；08:14已确认控制器及A0/A1 worker存活；随后用户回传worker日志确认新评价越过故障点。

| 阶段 | 最后证据 | 结论边界 |
|---|---|---|
| D26 | 2026-10-03 04:04，9/9完成 | 普通融合保留；复杂主候选未过gate |
| 原D27 | step0技术失败 | 不产生效果结论 |
| D27 repair | 2026-10-03 18:22，10/10完成 | 四科学gate失败 |
| D28 | 2026-10-03 19:27，7/7完成 | 压力gate失败，原件已重算 |
| D29 | 无启动证据 | 不激活 |
| D30 | 2026-10-04 00:47，六项完成 | P/R/PR_area/PR_pixel continue均False；完整原件待上传 |
| Post-D30 A | 2026-10-04 06:04 | 6/6训练到8000；6项评价失败；0项正式完成 |
| Post-D30 B/C | 同上 | 12项主体未开始 |
| Post-D30 F | 同上 | 4项条件待定，不可默认为必跑 |
| 评价修复 | 08:14队列存活＋随后worker日志（未附新时间） | A0/A1均新增训练更新0、复用20条记录；故障条件已评价，完整完成待核对 |

D30终端汇总：P综合86.092396，R84.037805，PR_area85.986496，PR_pixel84.759540，四项continue均False。相对S0综合86.051214，PR_area−0.064718pp、PR_pixel−1.291674pp；不同归一化未达到预设增量门槛。P的小改善与R的信息取舍仍成立，但不能据此认定唯一根因或整个双模态问题无效。指标为Potsdam开发Val2、native512/stride256、NoBoundary fg5的selected口径，来自用户终端；完整原矩阵尚待上传与独立重算。

[故障与恢复说明](../experiments/POST_D30_EVALUATION_REPAIR_20261004.md)、[原执行协议](../protocols/POST_D30_EXECUTION_20261003.md)、[机读设计](../../records/research_post_d30_design_20261003/plan.json)。

只使用物理GPU0/1，两张H10080GB，RAM与磁盘充足；seed42、8000步、物理batch16、无累积、nohup。快照/临时/缓存/日志均在/home/jovyan/zzx对应实验目录。用户在服务器终端执行，无SSH；不重复资源审计或预算探针。Test6及独立final禁止访问；重复开发Val2不等于独立泛化。GitHub本分支为共享权威，大预测/checkpoint保留服务器并索引。

[原始终端观测](../../records/research_post_d30_mechanisms_20261004T000812_2446364/failure_observation_20261004T060404.json)；[上一版状态](../history/pre_post_D30_evaluation_repair_20261004/PROJECT_STATUS.md)。


D30分析更新：六组selected汇总已整理；面积缩放PR_area对S1提高1.730941pp，但仍低于S0 0.064718pp，PR_pixel仍低于S0 1.291674pp，四项新配方continue均False。静态保护/恢复取舍明确，归一化缓解下降但未形成增量；固定checkpoint重放及loss/梯度原件尚未上传，不宣称唯一根因。[完成阶段分析](../experiments/D30_COMPLETED_REVIEW_20261004.md)。原Post-D30队列与gate保持不变。
