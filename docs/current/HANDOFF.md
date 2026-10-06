# 当前交接：N2固定配方失败，诊断支持N5优先，原件已验收

最后服务器记录以已上传原件为准：N2 queue观测2026-10-05T22:11:34.641183+08:00，N2_COMPLETE_AWAITING_STAGE_PROTOCOL、六组COMPLETE；诊断queue观测23:27:15.831648，DIAGNOSTICS_COMPLETE_AWAITING_REVIEW、E0/MASKS和五worker COMPLETE、新增训练0。2026-10-06已收到N2 a33872c和诊断7c47c49两次原件上传；本次助手只做GitHub回读/离线复算，没有新的服务器运行查询。

## 本次工作、证据与决定来源

独立验收PASS：1199载荷清单路径/大小无缺项，连两manifest共1201文件；298已读载荷上传/适用解码SHA通过，148618条矩阵/原始指标、19008次joint校验及固定gate复算匹配。未重读全部载荷、服务器权重/影像/预测/掩码本体。N2固定双向候选gate=False，S对空间控制−0.007028pp，方向/打乱增量均未过；按原门槛停止该3×3关系配方，不救窗口/预算/seed。

E1仅RGB缺失/H高DSM变化满足原N5问题门槛（A0/B1比U低0.651883/0.656097pp，两tile同号），L在RGB方向更容易；E0 N1-2 clean Full边界伤害率高于内部14.236/14.703pp，分母支持充足，但不能证明跨区传播是原因。E2 RGB漏报比硬回退约高1pp，误报完整RGB损失约6.4pp，DSM漏报效应小且跨tile异号；exact fallback不等于精度最优。

[完整结果](../experiments/POST_N2_E0_E1_E2_RESULTS_20261006.md)列原件提交、计数/签名/掩码绑定、N2六臂固定门槛、E0分母、E1四组合和E2所有成本。固定N2失败去留来自事前协议，不是助手另改门槛。N5优先/N3随后来自原证据驱动计划条件顺序；既有按规划条件排队授权保持；本次尚未启动新训练，具体族代码/登记仍待落实。N5若混合增强有效先定位强基线，不自动承诺双向互补贡献。

## 下一步不确定性及未采纳建议

优先检验固定N5-3混合暴露能否超过N5-1随机暴露且在预留T和原条件保护通过；每族同N1-2完整state重新开始，不按后验最高N2初始化，不因只RGB/H过问题门槛改成易赢配方。原四组、预算与match条件先完整落实。N3的问题提示很大，但边界本来更难，需局部/网格/单侧/双侧控制证明区域归属增量；N4仍无条件更新暴露证据。E2负的RGB漏报成本否定“硬回退总精度最优”的推断，不自动改模型或训练新置信网络。

未采纳N2扩大窗口/系数/预算/seed救gate、直接全跑13组、提前T/Test6、把多条件/像素当独立重复、纯高度因果/MNAR声明。当前主线不因N5普通增强问题触发而改变，失败是具体实现，不扩大为整个双模态问题失败。

## 执行、原件与交接

原N2科学86b6、修复9b196a2、原目录research_post_ab_followup_n2_20261005T085829_3456726；诊断883fccc及research_post_n2_diagnostics_20261005T131434_3591073已完成，不重启。两原件归档a33872c/7c47c49已接收，N2 controller_repair轻量证据已在归档中保留。actual fixed22/selected32已按86b6实际执行链校正说明；不改原plan/manifest。旧C/N1已验收、旧失败去留不变，D30全矩阵未由本轮补齐。

[下一步](NEXT_EXPERIMENT.md)；[独立审计](../../records/post_n2_offline_audit_20261006/README.md)；[上一交接归档](../history/HANDOFF_PRE_N2_RESULT_AUDIT_20261006.md)。

研究阶段可行性探索；主线RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复旁支。Potsdam fit12/Val2=3_11、5_10，native512/stride256、NoBoundary fg5主指标，Full诊断，seed42开发证据。只用GPU0/1，长任务nohup，全部记录/执行快照在zzx对应独立目录；用户执行终端，无SSH、无Test6/T提前评价/independent final、无追加seed或失败配方自动重跑，F/N6保持跳过。
