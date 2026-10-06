# 共享入口：N2与诊断已验收，N5优先的条件规划

最后服务器记录以已上传原件为准：N2 queue观测2026-10-05T22:11:34.641183+08:00，N2_COMPLETE_AWAITING_STAGE_PROTOCOL、六组COMPLETE；诊断queue观测23:27:15.831648，DIAGNOSTICS_COMPLETE_AWAITING_REVIEW、E0/MASKS和五worker COMPLETE、新增训练0。2026-10-06已收到N2 a33872c和诊断7c47c49两次原件上传；本次助手只做GitHub回读/离线复算，没有新的服务器运行查询。

按[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)→[索引](experiments/rebuild_v1/INDEX.md)读取。权威为66322/remote_sensing_frequency的rebuild-v1-protocol-20260915。

独立验收PASS：1199载荷清单路径/大小无缺项，连两manifest共1201文件；298已读载荷上传/适用解码SHA通过，148618条矩阵/原始指标、19008次joint校验及固定gate复算匹配。未重读全部载荷、服务器权重/影像/预测/掩码本体。N2固定双向候选gate=False，S对空间控制−0.007028pp，方向/打乱增量均未过；按原门槛停止该3×3关系配方，不救窗口/预算/seed。

E1仅RGB缺失/H高DSM变化满足原N5问题门槛（A0/B1比U低0.651883/0.656097pp，两tile同号），L在RGB方向更容易；E0 N1-2 clean Full边界伤害率高于内部14.236/14.703pp，分母支持充足，但不能证明跨区传播是原因。E2 RGB漏报比硬回退约高1pp，误报完整RGB损失约6.4pp，DSM漏报效应小且跨tile异号；exact fallback不等于精度最优。

完整指标、分母、混杂和11/11统计/因果谬误检查见[已验收结果](experiments/POST_N2_E0_E1_E2_RESULTS_20261006.md)。原N2继承文字“fixed10/selected22”与实际86b6 worker不一致；实际fixed22/selected32，执行/原件覆盖匹配，gate口径不改，原plan/code不覆盖。

下一阶段沿既有条件顺序优先落实N5四组，再依据N5验收与独立区域问题判断N3五组；N4仍等条件更新暴露证据。每族固定N1-2基座、不叠失败N2、不选后验最高组；T只在完整N5协议冻结后执行。具体新训练代码/排队尚未实施，两个问题门槛不是方法有效证明，13组不是自动全跑。

研究阶段可行性探索；主线RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复旁支。Potsdam fit12/Val2=3_11、5_10，native512/stride256、NoBoundary fg5主指标，Full诊断，seed42开发证据。只用GPU0/1，长任务nohup，全部记录/执行快照在zzx对应独立目录；用户执行终端，无SSH、无Test6/T提前评价/independent final、无追加seed或失败配方自动重跑，F/N6保持跳过。

C2/N1-3与A2/B3旧失败去留保持；[C/N1报告](experiments/POST_C_N1_RESULTS_20261005.md)、[A/B报告](experiments/POST_D30_AB_RESULTS_20261004.md)。本次接收不补齐D30全部历史矩阵。


2026-10-06用户要求扩展后续实验，见[扩展规划](protocols/POST_N2_EXPANDED_PORTFOLIO_20261006.md)：原N5/N3/N4共13组，加R1/R2各4组条件储备，理论上限21组；另列四项无训练诊断。第一批仍N5四组，尚未实现/登记新队列。新增储备不自动执行；本页前述13组是原规划范围。
