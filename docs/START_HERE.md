# 共享入口：M2后研究规划与未完成的最终清理（2026-10-29）

先读[研究决定](current/RESEARCH_DECISION.md)、[交接](current/HANDOFF.md)、[状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)。长期规则见[AGENTS](../AGENTS.md)、[执行约定](protocols/EXECUTION_CONTRACT.md)和[实验规划规则](protocols/EXPERIMENT_PLANNING_RULES.md)。

本轮新增：
- [A0双H100执行合同](experiments/POST_M2_A0_EXECUTION_20261029.md)与[首批脚本](../scripts/post_m2_a0.py)：本地代码及3项纯合同测试已完成；沿用原remote_sensing环境，必要时就地升级；服务器权重/吞吐待实测，尚未有新科学结果。
- [下一阶段能力先验与多路线计划](experiments/POST_M2_CAPABILITY_PRIOR_PLAN_20261029.md)：先单seed能力探针与四臂控制，有正向证据才扩大。
- [历史结论、原稿与近期文献核对](experiments/POST_M2_EVIDENCE_AND_LITERATURE_AUDIT_20261029.md)：区分具体失败与整个问题；纠正“信息上限/保证零伤害”等过度推断。
- [实验准备表](protocols/POST_M2_CAPABILITY_PREFLIGHT_20261029.md)和[机器计划](../records/post_m2_capability_plan_20261029/plan.json)：明确未测项、额外参考训练成本、停止点与小证据保留。

总体研究路线仍为条件规划；A0代码已准备、服务器未预检/未启动。没有新训练、模型下载或服务器队列修改。GitHub权威分支rebuild-v1-protocol-20260915供两台电脑接续；规划不代表已采纳更换主线或已得到方法效果。

M2主结果已登记：[科学报告](experiments/PHASE3_M2_ACCEPTANCE_AND_CLOSEOUT_20261029.md)、[中央索引](experiments/rebuild_v1/INDEX.md)、[注册表](../records/rebuild_v1_experiment_registry.json)。DF当前配方关闭，J工程停止单列。

另外仍待服务器回执：[零训练/零推理补充分析与最终清理](experiments/PHASE3_M2_FINAL_COMPACTION_20261029.md)。第一次真实清理后18权重是最后实际观测，新的目标0尚未确认；不重复第一次清理，不因候选研究保留无用大权重。共享数据/公共预训练不动；上传后回读关键文件，不例行重复哈希。
