# 共享入口：两轮已上传并有结果报告，下一方案待设计

权威分支66322/remote_sensing_frequency / rebuild-v1-protocol-20260915。本轮回查确认Post-T paired v2与Structured v0.1都有完整上传快照及既有结果分析，不再沿用07:36运行/等待状态。

上传最后观测：Post-T 2026-10-12T11:03:22.917566+08:00，8/8 COMPLETE；Structured 2026-10-12T16:32:44.762198+08:00，42/42 COMPLETE，640缺失＋8clean＋6旧端点，0训练。不是当前服务器实时查询。记录中的两轮均已收口，没有已登记的自动后继新实验；下一状态DESIGN_REVIEW_NOT_REGISTERED。

[Post-T结果](experiments/POST_T_PAIRED_V2_RESULTS_20261012.md)、[Structured结果](experiments/STRUCTURED_FAILURE_V0_RESULTS_20261012.md)、[本次关键原件复核](experiments/LATEST_RESULTS_KEY_REVIEW_20261012.md)。总gate保持PAIRED_SCREEN=False与NO_SUPPORT_THIS_PROTOCOL。

2026-10-12关键原件复核补充：R16−H16=+0.348562pp，两tile分别+0.328642/+0.356335pp，原screen中这一配对passed=True；R16总gate=False的直接原因是六E相对R0的五项底线失败，不是R−H配对未过。F/H/R独立8k/16k预算比较未通过收益门槛；R16自身8k→16k轨迹仍+0.618217pp，因此只关闭当前配方下盲目延长预算的依据，不宣称后半程不学习或普遍收敛。DSM特征内容干预是已存在的更直接线索：R16在块缺失条件C−Z=+4.009563pp、C−S=+9.114377pp；仍是固定模型推理敏感性，不是同预算RGB-only配对训练因果结论。

研究主线RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复旁支。现有交接提出可靠性/条件路由作为下一候选设计，尚无新训练协议或执行，不把它写成已验证方案；旧路由失败需纳入设计边界。不自动续训、改gate、换mask/seed/候选、扩Phase1B/Phase2，Test6/held4/final关闭；服务器由用户执行、无SSH，记录在/home/jovyan/zzx。

读取顺序：[新对话交接](current/NEW_CHAT_HANDOFF_20261011.md)→[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[PROJECT_STATUS](current/PROJECT_STATUS.md)→[NEXT_EXPERIMENT](current/NEXT_EXPERIMENT.md)→[实验索引](experiments/rebuild_v1/INDEX.md)→上述两轮结果及关键复核。
