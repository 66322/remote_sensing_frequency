# 状态：D30已完成；Post-D30技术停止

最新服务器观测2026-10-04T08:41:43.586227+08:00：队列CONTROLLER_INTERRUPTED，控制器2698383 LIVE=False；A0—A5已全部COMPLETE（分别08:22/08:31/08:41），6/18主体完成，B/C全PENDING、F待门槛，无活跃worker。A评价恢复已成功且未重训；阶段A汇总子进程抛出ModuleNotFoundError: No module named 'model'，随后控制器退出。这是脚本搜索路径缺失：cwd=code不自动把code加入独立脚本的sys.path。导入路径修复已本地实现并通过6项回归（含实际汇总子进程--help）；尚无服务器第二次恢复启动观测。恢复在同目录建立新覆盖快照，保留原plan/code及A完成标记，不重跑A，重新生成A阶段汇总后接B/C，仅GPU0/1。

历史运行观测：D30在2026-10-04T00:47:08.030508+08:00为COMPLETE，六项全部完成。Post-D30在2026-10-04T06:04:04.397991+08:00为COMPLETE_WITH_TECHNICAL_FAILURES；原控制器2450552已退出（Z、LIVE=False），无活跃worker。A0—A5均训练至8000步，均因评价条件`dsm_present_zero`未被处理而失败；0/18正式完成，B/C未启动，F仍待条件。不能据此评价A机制效果。原执行commit为01ec8dee82f7e272f6a650aaf9f3e619a0e7c516，原目录为`research_post_d30_mechanisms_20261004T000812_2446364`。该失败观测为06:04历史状态；08:41六项A完整完成，随后阶段汇总导入错误令控制器停止，第二次恢复待执行。

| 阶段 | 最后证据 | 结论边界 |
|---|---|---|
| D26 | 2026-10-03 04:04，9/9完成 | 普通融合保留；复杂主候选未过gate |
| 原D27 | step0技术失败 | 不产生效果结论 |
| D27 repair | 2026-10-03 18:22，10/10完成 | 四科学gate失败 |
| D28 | 2026-10-03 19:27，7/7完成 | 压力gate失败，原件已重算 |
| D29 | 无启动证据 | 不激活 |
| D30 | 2026-10-04 00:47，六项完成 | P/R/PR_area/PR_pixel continue均False；完整原件待上传 |
| Post-D30 A | 2026-10-04 08:41 | 6/6完整完成；保留全部权重及评价 |
| Post-D30 B/C | 同上 | 12项主体未开始 |
| Post-D30 F | 同上 | 4项条件待定，不可默认为必跑 |
| 评价修复 | 2026-10-04 08:41 | 六组A完整恢复；阶段汇总model导入失败，控制器退出 |

D30终端汇总：P综合86.092396，R84.037805，PR_area85.986496，PR_pixel84.759540，四项continue均False。相对S0综合86.051214，PR_area−0.064718pp、PR_pixel−1.291674pp；不同归一化未达到预设增量门槛。P的小改善与R的信息取舍仍成立，但不能据此认定唯一根因或整个双模态问题无效。指标为Potsdam开发Val2、native512/stride256、NoBoundary fg5的selected口径，来自用户终端；完整原矩阵尚待上传与独立重算。

[故障与恢复说明](../experiments/POST_D30_EVALUATION_REPAIR_20261004.md)、[原执行协议](../protocols/POST_D30_EXECUTION_20261003.md)、[机读设计](../../records/research_post_d30_design_20261003/plan.json)。

只使用物理GPU0/1，两张H10080GB，RAM与磁盘充足；seed42、8000步、物理batch16、无累积、nohup。快照/临时/缓存/日志均在/home/jovyan/zzx对应实验目录。用户在服务器终端执行，无SSH；不重复资源审计或预算探针。Test6及独立final禁止访问；重复开发Val2不等于独立泛化。GitHub本分支为共享权威，大预测/checkpoint保留服务器并索引。

[原始终端观测](../../records/research_post_d30_mechanisms_20261004T000812_2446364/failure_observation_20261004T060404.json)；[上一版状态](../history/pre_post_D30_evaluation_repair_20261004/PROJECT_STATUS.md)。


D30分析更新：六组selected汇总已整理；面积缩放PR_area对S1提高1.730941pp，但仍低于S0 0.064718pp，PR_pixel仍低于S0 1.291674pp，四项新配方continue均False。静态保护/恢复取舍明确，归一化缓解下降但未形成增量；固定checkpoint重放及loss/梯度原件尚未上传，不宣称唯一根因。[完成阶段分析](../experiments/D30_COMPLETED_REVIEW_20261004.md)。原Post-D30队列与gate保持不变。


D30原生紧凑证据已于214eb158a59cf8248910ba5e46492189d3a6f953上传，156文件、1134456字节；screen_result已回读。P仅综合门槛失败，最差tile/condition−0.076827pp；PR_area还存在最差−0.298852pp及fixed8000对S0−0.067831pp，不能称完全恢复安全性。PR_pixel仅DSM正确保留65.7654%、仅RGB正确90.1002%，QD伤害3.0660%，仍是明显信息取舍。完整逐tile原矩阵本体未上传，梯度原件已上传但尚未完成综合分析。
