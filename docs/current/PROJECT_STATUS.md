# 当前状态：M2 32/108，双种子clean局部负向，条件面板待完成（2026-10-25）

- 最后服务器观测2026-10-25 12:08:24+08:00：M2 RUNNING，32/108训练完成（29.63%）、失败/阻断0，34项有进度；两控制器及两GPU worker当时存活，合并WAIT_M2。完整故障面板`counted_cases=0`、`evaluation=null`，尚无M2阶段summary/gates。这不是实时状态或完整科学验收。[原样终端副本与分析](../experiments/PHASE3_M2_PROGRESS_AND_INTERIM_20261025T120824.md)。端点原始SHA和轨迹清单仍待最终验收。
- 12:08 GPU0 F0_s2026_DEntropy为18160/32000步、约0.338秒/步；GPU1 F0_s2026_DMix为29580/32000步、约0.243秒/步。两卡利用率52%/11%为瞬时采样，不据此诊断瓶颈或外推全队列ETA。剩余纯训练约1.30/0.16小时，仅针对两在途作业。
- 完整面板须任一外折36作业齐全且mask设计就绪才启动；年龄轨迹单独计数，因此counted_cases=0/evaluation=null和cpu_tasks=0不据此判故障。M2汇总须所有108及计数finalize后生成。
- 现有M2/combined revision目录及752d/25b124绑定不变，控制器2754693/2754694、GPU worker2757402/2757403在12:08观测存活。合并WAIT_M2正常；J/R/T/V未获得放行或实际运行新证据，B/C不开放。
- 当前继续已有队列，按[只读查看指南](../protocols/PHASE3_PROGRESS_AND_RESULTS.md)观察后续轨迹/首折完整评价，不再次启动、修复或删除回执，不自动重跑/补seed。GPU0/1、有界内存、test封存及用户执行无SSH保持。
- [长期启动规则](../protocols/STARTUP_DELIVERY_AND_FAILURE_CONTROL.md)继续生效；本轮无新训练或环境/运行代码修改。结束验收全部端点、原始整数计数、轨迹及额外修订材料，再整理轻量同步。
- 最新指标读取2026-10-25 12:08:24+08:00：[F0 seed17/42的32k clean表](../experiments/PHASE3_M2_PROGRESS_AND_INTERIM_20261025T120824.md)。两seed各七个DSM臂四tile齐全；DF相对同seed D0分别-0.6126/-0.5983pp。DSelf/DMix跨seed变号；seed2026缺D0，不能配对。这是中央512内缩开发集单模态结果，不是完整条件补救/融合面板或G1–G4判定。汇总器仅只读已有计数，未重训或重新推理。

- 2026-10-25[种子/吞吐规范落实复盘](../experiments/PHASE3_PLANNING_POLICY_AUDIT_20261025.md)：旧规则已存在但未完整落实，已补根/稳定入口和准备表。不是新实验结果或运行采样；当前108/三seed未缩减，GPU候选瓶颈仅代码定位、未目标profiling或优化。

- 2026-10-25用户采纳[按阶段证据调整研究](../protocols/ITERATIVE_RESEARCH_REVIEW_20261025.md)：已有运行中分析问题与简单对照，逐轮决定后续投入；地图线仍待数据/首轮验证，没有新增代码或结果。自动队列未增加人工暂停，未改seed/作业或抢占GPU。
- 磁盘新观测：10月25日00:22:02+08:00，文件系统10T/已用5.4T/可用4.7T/54%；inode已用和剩余未提供。随后无独立时间戳的env du回执：当前M2目录1.9G、combined目录134K。仅磁盘证据，不刷新GPU/进度；详见上述流程文末来源记录。
