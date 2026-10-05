# 状态与证据接收

最后服务器观测（用户回传）：2026-10-05T08:58:59.848681+08:00，N2控制器PID3456909已退出，QUEUE=CONTROLLER_INTERRUPTED。N2-0已派发到GPU0（worker PID3457210），其实际存活/训练步数待核对；不能把旧step=0快照当成当前进度。N2-1—5尚待派发。原科学执行提交86b6a70e5c3482314986fb1259e2fccbd0a5a38b保留。故障为per_job_timeout_hours=null被直接乘3600；这是控制器技术失败，不是N2科学负结果。控制器专用修复和安全接管工具已发布，尚无服务器恢复执行回报。先接管已有worker或验收绑定完成记录；已退出且未有效完成则HOLD、输出日志，不自动重训。不重复登记N2，不重启原C/N1。


最后服务器记录：原Post-D30于2026-10-05T00:26:01.590322+08:00 COMPLETE（18/18主体、F四项实际SKIPPED_GATE）；N1于07:21:14.003184 COMPLETE_AWAITING_STAGE_PROTOCOL（四项8000步、固定门槛False、N6三项实际SKIPPED_GATE）。两阶段轻量原件已上传并回读；C0—C5/N1-0—3十组20份summary的绑定、整数汇总和固定门槛复算通过。没有本次助手实时服务器查询。N2控制器已报错退出，N2-0已派发但实际进度待核对，安全接管待服务器执行；N3/N4/N5仍待各自诊断和协议，不把旧预约状态当可执行。

固定C2剩RGB对C0仅+0.041525pp、对C1−0.004058pp、对C3+0.028336pp；剩DSM对C0−0.041961pp、对C1−0.016106pp、对C3−0.026610pp，双侧门槛False。普通C0已解释DSM锚点改善，完整输入复用固定B0，不承诺蒸馏增量。N1-3对N1-2综合−0.881059pp、clean−0.852801pp、DSM缺失−0.156095pp，最差tile差−2.054791pp；固定gate=False。N2按事前规则使用N1-2作为匹配基座，不叠加失败多深度入口。

已接收原C轻量归档2535文件（2534载荷＋manifest），N1归档615文件（614载荷＋manifest）。两份清单路径/大小全部匹配；独立验收36份载荷上传/解码SHA、十份complete与20份summary执行/plan/完成绑定，77760矩阵tile→pooled、233280指标/原始计数记录、7560joint汇总及candidate边际；C2/N1checks重算一致。[审计和指标表](../experiments/POST_C_N1_RESULTS_20261005.md)。

A2/B3 gate保持False；A/B原件已收、旧关键七组复核保持，另外五组未在本次独立扩审。D23—D30既有整理保持，D30完整逐tile矩阵和部分早期原件仍未齐。

N2六组执行代码已实现，CPU8项检查与语法检查PASS；GPU0/1已登记，08:58:59控制器退出；N2-0当前worker进度待核对，真实权重CUDA、运行速度及精度还无回报。新增六组各8000步，不将已完成N1追训；N3/N4/N5没有可执行worker，N6三项实际跳过。[协议](../protocols/POST_AB_N2_EXECUTION_20261005.md)。

主线仍RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复是旁支；仍为可行性探索，无确认性新贡献。不重训A/B/C/N1、不增加seed或扫参、不启动F/N6、不访问Test6/independent final。服务器由用户终端执行，无SSH；只用GPU0/1两张H10080GB，每卡一worker，nohup；全部记录/快照/缓存在zzx对应独立目录，不重复资源审计。


本次控制器修复：None超时按原定8小时处理；验证PID/启动tick/任务参数、完成SHA及待派发目录。修复文件另存原N2实验的controller_repair_*，worker仍执行原86b6快照。CPU恢复11项（含实际监控循环）与原N2八项检查通过，七文件语法检查通过；这些不代表真实CUDA任务成功。详见[修复说明](../experiments/POST_AB_N2_CONTROLLER_REPAIR_20261005.md)。
