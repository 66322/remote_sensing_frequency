# 共享入口：M2补充分析与最终清理待服务器执行（2026-10-29）

先读[交接](current/HANDOFF.md)、[状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)、[研究决定](current/RESEARCH_DECISION.md)；长期规则见[AGENTS](../AGENTS.md)和[执行约定](protocols/EXECUTION_CONTRACT.md)。

用户要求删除剩余权重/推理等大文件，只留代码与小结果。已实现[零训练/零推理的补充分析和最终清理工具](experiments/PHASE3_M2_FINAL_COMPACTION_20261029.md)，12项本地检查通过，**服务器尚未执行**。先提取现成alpha/流量/逐类/边界/校准/掩码/训练轨迹结果，核对主结果后再删。不要重复第一次清理命令。

最近实际仍保留18个R/D0及原始统计，目标0权重待新回执确认。新策略会退役大统计/29.86MB重复包/完整batch逐步列表，保留小型矩阵、数值证据、配置、回执和必要压缩日志；共享数据与公共预训练不动。

GitHub分支rebuild-v1-protocol-20260915供两台电脑接续；主结论与代码在远端，新结果待服务器粘贴小摘要后同步。不把发布工具写成完成清理，不重复哈希，不要求固定电脑下载归档。J仍为工程停止，最终清理后不假定旧专家仍在，封存split不开放。

[M2科学报告](experiments/PHASE3_M2_ACCEPTANCE_AND_CLOSEOUT_20261029.md)、[中央索引](experiments/rebuild_v1/INDEX.md)、[注册表](../records/rebuild_v1_experiment_registry.json)已分别登记实际历史与新待执行事件。
