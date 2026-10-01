# Start Here

分支：`rebuild-v1-protocol-20260915`。实验快照基准：`1a8a840`；2026-10-01后续澄清研究定位，实验结论不变。不要把默认main或其他电脑旧目录视为本分支。

## 新对话按此顺序读取

1. [研究定位、候选路线与去留决策](current/RESEARCH_DECISION.md)：当前是论文可行性探索，允许换解法、换交叉问题或换方向；C1尚未取代原路线。
2. [当前交接](current/HANDOFF.md)与[当前状态](current/PROJECT_STATUS.md)：最新带时间的观测、证据范围和已作决定。
3. [下一步](current/NEXT_EXPERIMENT.md)：先梳理问题与未决机制；条件计划不等于已授权启动。
4. [不可重复事项](current/DO_NOT_REPEAT.md)、[实验索引](experiments/rebuild_v1/INDEX.md)及[机器台账](../records/rebuild_v1_experiment_registry.json)：核对已完成/关闭工作，再进入原始协议、配置、源码和证据。
5. [实验准备规则](protocols/EXPERIMENT_PLANNING_RULES.md)与[准备表](templates/EXPERIMENT_PREFLIGHT_TEMPLATE.md)：实际有界吞吐测试、默认单种子、资源与下载说明。

优先评估频率与语义可靠性融合，以及模态缺失/退化时的训练和推理能力；具体机制必须由证据决定。C1任务驱动恢复保留为旁支与潜在备选，部分解冻保留为强基线线索。近期正结果不自动改变论文方向，具体方案失败也不等于整个问题已被否定。

## 证据导航

- [Post-D21 42项与混合退化4项结果](experiments/POST_D21_FINAL_AND_MIXED_FOLLOWUP_RESULTS_20261001.md)
- [混合退化逐tile风险](experiments/POST_D21_MIXED_TILE_RISK_RESULTS_20261001.md)
- [D21有效双种子结果](experiments/D21_DETAIL_FREQUENCY_RESULTS_20260929.md)
- [已完成吞吐短测结果](experiments/POST_D21_THROUGHPUT_PROBE_RESULTS_20260929.md)
- [已执行多方向方案](protocols/POST_D21_MULTIDIRECTION_DAY_PLAN_20260929.md)与[历史执行说明](protocols/POST_D21_DAY_EXECUTION_20260929.md)
- [被替代的旧D22草案](protocols/D22_STRUCTURE_ALIGNED_DSM_RELIABILITY_DRAFT_20260929.md)

Post-D21完整逐任务摘要及大型原始产物尚未全部归档到GitHub；紧凑汇总不是全部原始证据。独立来源只在相应外部检验前验收，不阻塞合理的已有数据探索。Test6及独立final继续保持既有封存边界。本次入口更新不安排新GPU任务。此前入口见[历史快照](history/20261001_before_strategy_clarification/docs/START_HERE.md)。
