# 共享入口：D28复核完成，D30继续既定诊断

权威仓库66322/remote_sensing_frequency，分支rebuild-v1-protocol-20260915。先读[研究决定](current/RESEARCH_DECISION.md)→[交接](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)，再沿证据链接核对代码和原件；本地仅工作副本。

D28完成并上传38b85f5。238份tile原件重算一致：普通融合仍有益，共同受损额外损失仅0.014570pp，未过0.3pp筛选，复杂路由没有被新条件救活。[完整分析](experiments/D28_FINAL_REVIEW_20261003.md)。

D30已实际接力；最后直接观测2026-10-03 20:56:13+08:00存活、重放12/48，四训练PENDING，不代表当前实时进度。继续查现有队列，不重复启动或资源审计；原D29未激活，未新增多种子。[D30协议](protocols/D30_LOSS_DECOMPOSITION_AFTER_D28_20261003.md)。

主问题与候选/旁支角色未改变。仅GPU0/1 H10080GB、RAM/磁盘充足、batch16无累积、nohup、zzx对应实验目录；Test6禁读。旧入口已[归档](history/pre_D28_review_20261003/START_HERE.md)，旧“D28未读取/18:34 RUNNING”不作为当前事实。
