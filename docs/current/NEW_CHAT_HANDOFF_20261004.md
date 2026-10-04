请继续66322/remote_sensing_frequency，分支rebuild-v1-protocol-20260915，以GitHub为准。先读docs/START_HERE.md及docs/current/RESEARCH_DECISION.md、HANDOFF.md、PROJECT_STATUS.md、NEXT_EXPERIMENT.md，再读docs/experiments/rebuild_v1/INDEX.md和COMPLETED_EXPERIMENTS_HANDOFF_20261004.md。

主线仍是RGB–DSM双向条件互补与退化/缺失分割；频率、门控、MoE、共享私有是候选解法，任务驱动恢复只是旁支。D23—D28已分析；D30六项完成、紧凑原件已上传，四项新损失continue均False，完整逐tile矩阵仍在服务器。不要自动加种子或重跑失败配方。

最新服务器观测2026-10-04 08:41:43：Post-D30 A0—A5六项完成，6/18主体，B/C待运行、F仅B3过gate触发；汇总导入错误使控制器退出。第二次修复2a15ef163c3df7e96ee52c81cb677ebdb1305935已发布但尚无执行回报。先查询原队列；若已恢复就沿用，若仍停止按NEXT_EXPERIMENT同目录恢复，不重训/重评价A。接收A原生结果后按固定候选分析。

服务器由我执行终端，无SSH；根目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro，Post目录records/research_post_d30_mechanisms_20261004T000812_2446364。只用GPU0/1，两张H10080GB，RAM/硬盘充足；nohup，8000步、batch16、无累积。全部记录/缓存/快照在zzx对应目录。不要重复资源审计；不读Test6/独立final。后续重要记录、结论与交接继续写回同一GitHub分支并回读验证。
