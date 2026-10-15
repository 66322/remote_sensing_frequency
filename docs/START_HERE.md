# 共享入口：Phase3-M2长程设计已登记，尚未实现/启动（2026-10-16）

先读 [研究决定](current/RESEARCH_DECISION.md)、[当前交接](current/HANDOFF.md)、[状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)，再读 [M2完整计划](protocols/PHASE3_M2_ERROR_CORRESPONDENCE_20261015.md) 和 [计划清单](../configs/phase3_m2_plan_manifest.json)。

用户根据已完成结果要求安排GPU0/1长程实验，不限时间、优先研究问题与创新性。新问题是“错误位置对应性是否带来可迁移、可兑现的条件补救”。核心3个Fit12外层分组×3个整系统seed，108个32k训练、345.6万更新；条件反向与第二编码器储备合计上限279个、892.8万更新。后续阶段受科学门禁与实现冻结约束，不是全部自动启动。

状态为DESIGN_RECORDED_NOT_IMPLEMENTED_NOT_LAUNCHED。新执行器、精确fold表和执行提交尚待落实；无新run/PID。不要运行旧M1 bootstrap或恢复旧队列。

[Phase3-M1验收](experiments/PHASE3_M1_ACCEPTANCE_AND_ROUTE_REVIEW_20261015.md)与[Phase2.4验收](experiments/PHASE_24_ACCEPTANCE_AND_ROUTE_REVIEW_20261015.md)保持原科学结论，旧幅度配方关闭。Test6/held4/final禁读；旧Val2本轮不进入队列；全Fit12微调模型不能泄漏进入新外层主比较。另一篇点云论文不进入本篇。
