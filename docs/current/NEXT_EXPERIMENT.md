# 下一步：优先落实N5完整四组，当前不重启旧队列

最后服务器记录以已上传原件为准：N2 queue观测2026-10-05T22:11:34.641183+08:00，N2_COMPLETE_AWAITING_STAGE_PROTOCOL、六组COMPLETE；诊断queue观测23:27:15.831648，DIAGNOSTICS_COMPLETE_AWAITING_REVIEW、E0/MASKS和五worker COMPLETE、新增训练0。2026-10-06已收到N2 a33872c和诊断7c47c49两次原件上传；本次助手只做GitHub回读/离线复算，没有新的服务器运行查询。

N2与诊断两份原件已上传并回读验收，不需再次上传同一结果或再次运行已完成任务。[结果报告](../experiments/POST_N2_E0_E1_E2_RESULTS_20261006.md)确认N2原科学gate失败；E1只有RGB/H问题成立，E0提示边界困难，E2硬回退非精度最优。

## 下一研究族：按原规划先N5

N5不是本次已经派发的任务。沿既有条件计划先落实完整执行协议/代码与匹配CPU检查，再由用户服务器终端登记四组；主线不改、暂不同时启动N3/N4。

- 四组固定：N5-0原条件序列；N5-1 U随机块；N5-2 H/L内容块各半；N5-3 U半、H/L各四分之一的固定候选。
- 每族所有组重新从固定N1-2完整state SHA28bc6f8ca5e1221392598b0a6f2d160e8c633a6a9cf63827067df3e7b81a144b出发，同新8000步/batch16/seed42、同augmentation槽/方向/面积和有效监督口径。不沿失败N2继续、不按后验最优初始化。
- mask仅fit12输入内容，无标签/Val2错误选位；U/H/L whole-tile定义/配对形状固定。T规则不提前评价，必须完整N5训练配方、掩码、预算和判定冻结后再执行预留评价。
- 主比较N5-3对N5-1，T平均≥0.5pp、两tile正，同年龄同号；方向分开报告及clean/全缺失/旧条件保护底线保持。仅训H/L变好或U追平则关闭当前混合暴露的增量承诺。
- 不因E1只RGB/H通过就事后删L或只选方向、改T/强度救gate。若需要另立专门单向问题，明确新假设/协议，不能当原N5成功。

完整gate、对照和停止条件以[原规划](../protocols/POST_N2_EVIDENCE_LED_PLAN_20261005.md)为准；目前此页为落实待办，不是可执行服务器命令。N3五组等N5完成后独立区域问题，N4四组仍无更新暴露证据，13配置是条件上限。N5若普通混合增强有效先定位强基线，不直接称双向互补机制创新。

研究阶段可行性探索；主线RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复旁支。Potsdam fit12/Val2=3_11、5_10，native512/stride256、NoBoundary fg5主指标，Full诊断，seed42开发证据。只用GPU0/1，长任务nohup，全部记录/执行快照在zzx对应独立目录；用户执行终端，无SSH、无Test6/T提前评价/independent final、无追加seed或失败配方自动重跑，F/N6保持跳过。

[独立审计结果/复算方式](../../records/post_n2_offline_audit_20261006/README.md)；[研究决定](RESEARCH_DECISION.md)；[交接](HANDOFF.md)。
