# 研究决定：保持双向互补问题，授权新机制对照

主问题仍为RGB外观/语义与DSM高度/几何的双向条件互补及任一模态退化/缺失下的可靠分割。处于论文可行性探索，频率、语义可靠性、专家与共享/私有只是候选解法；任务驱动SR/恢复仍为旁支，没有自动转向或确认性贡献。

决策来源：用户要求根据D30四项结果实施原12＋4计划，并允许多安排几组、实验时间充足。现授权A/B/C各6组，18组主体；F4仍按原B3固定gate条件执行。新增A4/A5对齐强度、B5/B6搜索范围、C4/C5单向蒸馏是诊断，不用最佳结果替代预设A2/B3/C2的gate。没有多seed确认或新地区/test授权。

D27四gate、D28压力gate保持失败；原D29不激活。D30继续已授权损失拆解，P微小增量、R约2pp损失、正交互仅部分抵消，不能提前诊断唯一根因。PR_area/PR_pixel和原件仍待核对。

下一不确定性：仅共享对齐是否超过普通融合和全特征对齐；局部对应是否超过普通错位增强；缺失蒸馏是否超过直接任务适配及同mask硬监督、且两种缺失都受益；若对应成立，feature高频何时有用。每项以匹配新A0或专属对照判断，不能混用旧augmentation分数。

[四项结果分析](../experiments/D30_FOUR_ARM_REVIEW_20261003.md)、[执行协议](../protocols/POST_D30_EXECUTION_20261003.md)、[机读计划](../../records/research_post_d30_design_20261003/plan.json)。

能力分开报告：known availability精确回退（A/B/F）、C学习缺失精度、合成未知位置误差、独立地域泛化。C不再承诺单侧logits恒等；标签/退化真值仅训练监督或离线评价，禁止推理泄漏。两种输入同时无信息不承诺正常分割。

只使用物理GPU0/1，两张H10080GB；RAM/磁盘充足，无资源探针。seed42、8000步、batch16无累积、nohup。快照、临时、缓存、日志全部在/home/jovyan/zzx对应实验目录。用户在服务器终端执行，无SSH；Test6与独立final禁读。重复开发Val2不是确认性泛化证据。GitHub本分支为共享权威，大预测/checkpoint本体留服务器并索引。

历史角色与去留框架完整保留在[旧决定](../history/pre_post_D30_execution_20261003/RESEARCH_DECISION.md)。新机制失败不扩大为整个研究问题无效；通过单seed开发gate后只选一条另立确认协议。最后用户回传检查：Post-D30队列2026-10-04T00:11:46.062560+08:00为WAITING_D30，控制器PID2450552 LIVE=True，18主体0完成、22配置任务均PENDING且无活跃worker；D30队列2026-10-04T00:11:52.142311+08:00仍RUNNING、LOCK_FREE=False。正常等待前序释放，尚未开始新GPU训练。执行commit固定01ec8dee82f7e272f6a650aaf9f3e619a0e7c516，目录`research_post_d30_mechanisms_20261004T000812_2446364`。这次未提供D30各job步数/评价进度，不能继续引用23:17的步数为当前进度，不能更新剩余时间估计；四项完成指标已分析，PR_area/PR_pixel、重放效果及原矩阵待收。ps的ELAPSED字段数值异常，不作为运行时长或ETA依据。

[本次启动观测](../../records/research_post_d30_mechanisms_20261004T000812_2446364/launch_observation_20261004T000812.json)。

[00:11存活与等待观测](../../records/research_post_d30_mechanisms_20261004T000812_2446364/progress_observation_20261004T001146.json)。
