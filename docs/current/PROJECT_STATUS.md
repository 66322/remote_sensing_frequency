# 当前状态：M2完成17/108、失败0，双GPU加权对照训练（2026-10-24）

- 最后服务器观测2026-10-24 22:49:33+08:00：M2 RUNNING，控制器报告完成17/108训练作业、失败/阻断0，19个作业有progress；GPU0 F0_s17_DShuffle为16600/32000，GPU1 F0_s17_DEntropy为11420/32000。两控制器及两GPU worker存活，合并WAIT_M2。当前完整故障面板counted_cases=0、evaluation=null，尚无M2阶段summary。这是最后观测，不是实时状态或完整科学验收。
- [原样终端副本与进度解释](../experiments/PHASE3_M2_PROGRESS_20261024T224933.md)。控制器报告完成17/108约15.74%；若计入两在途作业，优化更新约16.55%，不含评价/计数，也不等于全队列墙钟完成率。端点和完整轨迹清单仍待验收。
- 当前GPU0 DShuffle为16600步、GPU1 DEntropy为11420步；稳定0.34994/0.34754秒每步，剩余纯优化1.50/1.99小时，不含后续评价与其他作业。两卡各8297MiB（约8.1GiB），GPU利用率为瞬时采样，不据此改预算。
- 完整面板须任一外折36作业齐全且mask设计就绪才启动；年龄轨迹单独计数，因此counted_cases=0/evaluation=null和cpu_tasks=0不据此判故障。M2汇总须所有108及计数finalize后生成。
- 现有M2/combined revision目录及752d/25b124绑定不变，控制器2754693/2754694、GPU worker2757402/2757403在22:49观测存活。合并WAIT_M2正常；J/R/T/V未获得放行或实际运行新证据，B/C不开放。
- 当前继续已有队列，按[只读查看指南](../protocols/PHASE3_PROGRESS_AND_RESULTS.md)观察后续轨迹/首折完整评价，不再次启动、修复或删除回执，不自动重跑/补seed。GPU0/1、有界内存、test封存及用户执行无SSH保持。
- [长期启动规则](../protocols/STARTUP_DELIVERY_AND_FAILURE_CONTROL.md)继续生效；本轮无新训练或环境/运行代码修改。结束验收全部端点、原始整数计数、轨迹及额外修订材料，再整理轻量同步。