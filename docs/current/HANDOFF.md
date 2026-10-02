# 当前交接：D26固定九组已获授权、实现和CPU检查

更新2026-10-02；[前次交接](../history/HANDOFF_20261002_BEFORE_D26_IMPLEMENTATION.md)。用户明确“按上述实验规划进行具体实验”，执行范围仅D26九组×8000=72000更新。代码CODE_COMMIT_PENDING；尚未收到服务器D26启动观测，不能说已经运行。下一动作是[一次nohup启动](../protocols/D26_EXECUTION_20261002.md)，不再资源探针、重训单模态或重复询问许可。

研究阶段为可行性探索。主问题RGB–DSM双方互补和任一方退化/缺失。频率/语义有独立容量/空间/打乱对照，不承诺都成立；J0联合适配强对照，C1任务恢复仍旁支，最终贡献未冻结。没有方向变更，D23—D25旧失败判定不改。

历史已有结论见[汇总](../experiments/RESEARCH_SYNTHESIS_D15_D25_20261002.md)，不是实验全部无效；未确立的是超出强基线、可归因且有独立泛化的新机制。最后服务器观测2026-10-02T15:14:54.351476+08:00：D25 COMPLETE8/8，原件2290b39、复核39ed183，旧目录records/research_d25_missingness_20261002T130253_1358078，不重新启动。

D26使用P6 selected2000 SHA bef8dda6537b68fc51f300bc3789bbbef57682baedf92a3f7665217a4a2fde71和D15 seed42 best15000 SHA d597f1adf3ca0291dcd7d063af941bebf3db1e61205cfdaf13271fbba9437e84；真实路径和原预处理已绑定。两真实独立专家、异构预训练/历史，所有九组同一对；J0只更新两末四block/decoder，其余冻结。分类前特征投影stride4/派生stride8，双向交互，与旧R0/M0输出gate不同。

机读[plan](../../records/research_d26_plan_20261002/plan.json)与[实现细化](../protocols/D26_EXECUTION_20261002.md)均在看D26结果前冻结。15CPU行为、原DSM random64 forward/梯度93/93、25Python3.10语法、26快照/5CLI通过。未加载服务器权重、未执行GPU/真实DINO训练；GPU2.2.2首正常batch内验证梯度。J0保留原DSM bilinear decoder CUDA非确定性warning，不声明比特重复；所有BN统计/专家dropout固定eval。

两GPU动态队列，物理batch16无累积，8线程常驻tile预取，不测资源预算。8000步固定，两时刻以三状态Val2 NoBoundary fg5 mean选模；固定8000十主条件诊断、selected22条件，双方退化/整幅局部缺失、互补缺失/双缺失无效区均保存。预测、6×6原计数、6^4 lossless sparse joint、SHA绑定可离线重算；共享只读原专家cache避免重复推理。冻结全缺失回退是工程保证，不是新精度贡献。

去留见[协议第7节](../protocols/D26_BIDIRECTIONAL_FEATURE_PLAN_20261002.md)：主要XSF超过B0/CAP/X、保护clean/各质量族/tile/缺失并与J0比较；S/F各独立增量和打乱，only-correct保留率独立门槛。阈值不变，失败关闭本轮载体/机制，不自动扫参或追训；通过最多一条另立seed与真正独立来源确认。

资源沿用GPU0/1两H10080GB、RAM/磁盘充足；所有新产物/code/临时/cache/PID在/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d26_bidirectional_<timestamp>_<pid>，nohup。无SSH由用户执行命令，启动/完成回传再更新服务器状态；不把发布当启动。Test6禁读，D15 Train16使held4不是未见final，Val2仅开发。新对话只需读上述GitHub入口，不重做审计。
