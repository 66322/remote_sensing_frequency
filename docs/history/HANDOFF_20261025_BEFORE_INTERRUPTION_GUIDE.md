# 当前交接：M2 45/108、F0条件评价在途（2026-10-25）

用户最新决定是边运行边检验实验目的，按结果调整后续研究；见[阶段复盘流程](../protocols/ITERATIVE_RESEARCH_REVIEW_20261025.md)。主线仍是RGB–DSM条件互补与退化/缺失分割、恢复旁支；连续建筑地图维护为独立优先候选，尚未验包/实现/训练，未取代主线。新路线先数据与现象、两基线×三地理划分×seed42六作业；简单重置已足够则不扩复杂机制。研究准备可并行，服务器资源仍按现有任务安排。

## 最近证据分别计时

- 进程/GPU：最后完整观测2026-10-25 22:12:38+08:00，M2 RUNNING 45/108，失败/阻断0，两控制器与两worker当时存活，combined WAIT_M2。两在途F1_s42_DClean/DShuffle为24520/8360步，约0.225/0.363秒/步；F0评价已计399例、仍处于`rgb_fault`，summary/gates未生成。[原回执及分析](../experiments/PHASE3_M2_PROGRESS_20261025T221238.md)。不是实时状态。
- 指标：22:12只读表的F0 seed17/42/2026七DSM臂32k四tile结果与20:35相同，DF−D0分别-0.6126/-0.5983/-0.9301pp；DF均低于DShuffle。clean局部负向不代替条件补救/融合或G3；full-GT为同中央计分域全标签，不是全tile。三seed共享F0外折，不能当独立地区验证。F1仍缺D0配对。
- 磁盘：10月25日00:22:02文件系统10T、已用5.4T、可用4.7T、54%，inode已用/剩余未报告；随后无独立时间戳的env du：M2 1.9G、combined 134K。未刷新进程/GPU/训练数，不凭目录大小推断完成。

## 当前目录及绑定

- M2：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m2_revision_20261024T092814_2738345
- 合并：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_combined_revision_20261024T092814_2738345
- 科学源M2 ac325cdbb403ebb95b5eb0acbf17fffa5441dcfd、合并e65c6cb0830985461b3cd30e2f43158dd3d858cb；工程752d3835a18a15a04d83b1dcc1841bff98bf0b07、包路径25b124a0cf69ececb6841b55ed90b19fae5b9a08；只读中间汇总624194105b3b018bb1e1e66d80cada2a405e7758。
- 单次启动回执records/phase3_engineering_restart_20261024_once.json，原失败目录与修复材料保留。运行代码未改，当前M2仍108/三seed，合并最多228/5088000更新；未宣称已缩减种子或完成GPU提速。

## 立即下一步及执行边界

F0外折36项训练已齐、故障评价在途；下一关键证据是完整补救/损伤/融合面板及原始整数计数，不能把399例当完整评价。M2剩63项，20:35至22:12新增2项/1.625小时；机械等速外推约51小时，与先前约50小时情景相近，但实际作业结构和评价耗时未定，仍按约2–4天资源窗口准备而非确定完成日。阶段汇总仍按108及计数finalize；原G0通过可自动进入J/R，研究复盘节点没有新增人工暂停功能。具体缩减/改排可以讨论和修订，须同步执行依赖与判定、披露已看结果并保留全部证据；本轮没有队列变更。

按需只读运行已有records/phase3_engineering_restart_package_752d3835a18a15a04d83b1dcc1841bff98bf0b07/scripts/status_phase3_engineering_restart.py，见[查看指南](../protocols/PHASE3_PROGRESS_AND_RESULTS.md)。不重复bootstrap/repair --apply/改环境/重启。发现实际错误保留首栈并按既有首败规则处理，不自动重跑。T/V缺任一数据catalog时等待；B/C未开放。GPU0/1、用户执行无SSH、内存优先、test封存保持。

[种子/吞吐复盘](../experiments/PHASE3_PLANNING_POLICY_AUDIT_20261025.md)：旧规则已存在但未完整落实。新计划必读[规划规范](../protocols/EXPERIMENT_PLANNING_RULES.md)，探索默认单seed、必要重复通常先42/17，第三须理由与成本。GPU小批教师、分层循环与每步同步仅候选瓶颈，未目标profiling；新增/改动按受影响范围验证，复用未变证据，不因换对话/补规则重跑全面审计。

结束核验原端点/整数计数/样本流/训练轨迹及752d/25b修订材料；[数据保存规则](../experiments/PHASE3_DATA_AND_ARTIFACT_STORAGE_20261024.md)。服务器publication不等于全部已上传GitHub，重要结论须同步并回读。[启动约定](../protocols/STARTUP_DELIVERY_AND_FAILURE_CONTROL.md)、[稳定新对话入口](../current/NEW_CHAT_HANDOFF.md)。[本次更新前交接归档](HANDOFF_20261025_BEFORE_M2_45_PROGRESS.md)。
