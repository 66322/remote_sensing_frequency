# 共享入口：多路线研究规划 v2（2026-10-30）

先读[研究决定](current/RESEARCH_DECISION.md)、[交接](current/HANDOFF.md)、[状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)。长期规则见[AGENTS](../AGENTS.md)、[执行约定](protocols/EXECUTION_CONTRACT.md)和[实验规划规则](protocols/EXPERIMENT_PLANNING_RULES.md)。

本轮按用户要求扩展为多问题、多路线探索，不再把A0阳性当所有路线的前置：

- [多路线主计划](experiments/POST_M2_MULTIROUTE_PLAN_20261030.md)：A表示、G几何、Q质量训练、S结构读出、C特权蒸馏、P适配泛化；E优化/可靠性、F地图维护分别保留。
- [2025—2026文献与迁移矩阵](experiments/POST_M2_MULTIROUTE_LITERATURE_20261030.md)：MM-DINO直接近邻，LiDeRe/AnyUp强读出，GKD、DFormerv2、MIAM、SGMA等及原附件论断核验。
- [新准备表](protocols/POST_M2_MULTIROUTE_PREFLIGHT_20261030.md)与[机器计划](../records/post_m2_multiroute_plan_20261030/plan.json)：首轮建议15作业/96k，seed42；新实现/吞吐/队列均未完成。
- [A0执行合同](experiments/POST_M2_A0_EXECUTION_20261029.md)继续固定c22a046407daf42064cbb161429f2648c9b86d66；已有DINOv2检查无需重复。原[能力先验计划](experiments/POST_M2_CAPABILITY_PRIOR_PLAN_20261029.md)保留为历史及A1/A2分支合同，整个组合入口由v2取代。

最后服务器回执为2026-10-29 20:18:55：DINOv2 profile完成；没有收到A0正式训练/DINOv3下载与加载完成回执。本次只更新规划，未操作服务器。两张H100可用是历史观测，启动前沿相应合同确认实际状态。

M2主结果与配方关闭见[验收](experiments/PHASE3_M2_ACCEPTANCE_AND_CLOSEOUT_20261029.md)；J工程停止。M2[最终清理](experiments/PHASE3_M2_FINAL_COMPACTION_20261029.md)在预删除统计阶段报错后暂缓，最后确认剩18端点，不能写0。清理授权不因新研究撤回，旧专家不假设免费可用。

GitHub分支rebuild-v1-protocol-20260915为两台电脑共享权威；文档发布不代表控制器部署或实验成功。
