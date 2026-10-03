# 共享入口：D28复核完成，D30继续既定诊断

## 2026-10-03新增规划：12组主体＋4组条件实验

用户要求结合实验与近期论文多规划几组，已形成[后续组合计划](protocols/POST_D30_PORTFOLIO_20261003.md)及[论文核对](literature/POST_D28_MECHANISM_READING_20261003.md)。A四组比较全特征/共享对齐与错配；B四新组＋复用A0构成局部对应×增强及错配对照；C四组比较双向缺失任务适配/蒸馏/教师正确筛选/同mask硬CE；F四组仅在B通过后检验两侧高频。先A/B八组，再C四组；每组拟seed42、8000步，未新增多seed。普通单模态锚点复用。

状态明确：**仅规划，未实现、未排队、未启动**。这是用户要求下的新机制建议，不改变D27/D28旧门槛，不激活D29，不改D30队列。计划写明匹配对照、继承预算、额外计算、候选停止条件与未实现接口；执行授权和真实排队状态另记录。主问题/候选/旁支角色不变，不能把规划中的新机制当已验证贡献。D30最后观测仍为下述20:56，没有新实时查询。

权威仓库66322/remote_sensing_frequency，分支rebuild-v1-protocol-20260915。先读[研究决定](current/RESEARCH_DECISION.md)→[交接](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)，再沿证据链接核对代码和原件；本地仅工作副本。

D28完成并上传38b85f5。238份tile原件重算一致：普通融合仍有益，共同受损额外损失仅0.014570pp，未过0.3pp筛选，复杂路由没有被新条件救活。[完整分析](experiments/D28_FINAL_REVIEW_20261003.md)。

D30已实际接力；最后直接观测2026-10-03 20:56:13+08:00存活、重放12/48，四训练PENDING，不代表当前实时进度。继续查现有队列，不重复启动或资源审计；原D29未激活，未新增多种子。[D30协议](protocols/D30_LOSS_DECOMPOSITION_AFTER_D28_20261003.md)。

主问题与候选/旁支角色未改变。仅GPU0/1 H10080GB、RAM/磁盘充足、batch16无累积、nohup、zzx对应实验目录；Test6禁读。旧入口已[归档](history/pre_D28_review_20261003/START_HERE.md)，旧“D28未读取/18:34 RUNNING”不作为当前事实。
