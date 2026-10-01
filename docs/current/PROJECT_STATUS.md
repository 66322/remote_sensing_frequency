# 当前项目状态

## 研究决策状态（2026-10-01澄清）

当前处于论文可行性探索。优先评估频率与语义可靠性融合及模态退化/缺失条件下的训练、推理能力；允许同题换解法、换交叉问题或换方向。C1是旁支开发候选，未决定取代原路线；A部分解冻是基线策略。最终方法与章节结构未冻结。详见[研究定位与决策](RESEARCH_DECISION.md)。

已有证据与未决机制梳理已完成，见[证据缺口报告](../experiments/RESEARCH_GAPS_AND_DECISION_20261001.md)。下一步建议D23-A先查固定专家互补空间，满足资源投入条件才准备D23-B完整语义/频率收益门控；A的CPU计数工具已实现并通过7项本地合成检查，真实服务器profile/计数未运行；B仍为未实现方案。用户将在终端执行[有界CPU命令](../protocols/D23_A_CPU_EXECUTION_20261001.md)。独立来源验收是外部评价条件，不是所有探索的绝对前置。文档澄清没有新增实验观测或训练授权。

## 最后带时钟的服务器观测：2026-10-01 10:15:16+08:00

Post-D21 原队列 `42/42 COMPLETE`；后续混合退化 C0/C1 四任务队列自动衔接并 `4/4 COMPLETE`、整数审计 `PASS`。10:15 的新观测是服务器逐 tile CPU 审计 `PASS`，结果由用户推送至[诊断 JSON](../../records/post_d21_mixed_followup_compact_20260930/tile_risk_diagnostics.json)。这是历史运行记录，不代表当前 GPU 实时状态。两份 `analysis.json` 均报告 Test6 未加载；[总体开发集结果](../experiments/POST_D21_FINAL_AND_MIXED_FOLLOWUP_RESULTS_20261001.md)及[逐 tile 风险](../experiments/POST_D21_MIXED_TILE_RISK_RESULTS_20261001.md)已记录。原始评价摘要与 checkpoint 仍在服务器，本地没有重新评价影像或哈希 checkpoint 二进制。

研究判断：A 的部分解冻是强基线改进而非 DSM 专属收益；B3 与 C3 未过冻结门槛；D 的联合恢复损失×DSM 交互为负；C1 可学习恢复相对 C0 在固定倍率四块及混合退化八个 pooled 条件均正，但 Vaihingen 局部 tile 退化。tile20 主要见 Car 误报增多，tile33 在未见模糊下见 Building/LowVegetation 漏检与 Tree 误报增多。证据仅限单 seed42、Potsdam Val2 / Vaihingen 同镶嵌图开发区；Test6/独立 final 继续封存；旧Test6已有历史开发暴露，不具诚实独立final资格。当前待办见[可行性判断与条件实验计划](NEXT_EXPERIMENT.md)，本次未启动新训练。旧状态归档于[历史](../history/20261001_before_final_post_d21_results/PROJECT_STATUS.md)。
