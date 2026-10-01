> 最新D23-A服务器观测2026-10-01T12:44:35.075903+08:00（用户回传）：COMPLETE、eligible_to_prepare_B=true。下方Post-D21时钟为此前实验历史观测，不代表当前GPU状态。

# 当前项目状态

## 研究决策状态（2026-10-01澄清）

当前处于论文可行性探索。优先评估频率与语义可靠性融合及模态退化/缺失条件下的训练、推理能力；允许同题换解法、换交叉问题或换方向。C1是旁支开发候选，未决定取代原路线；A部分解冻是基线策略。最终方法与章节结构未冻结。详见[研究定位与决策](RESEARCH_DECISION.md)。

已有证据与未决机制梳理已完成，见[证据缺口报告](../experiments/RESEARCH_GAPS_AND_DECISION_20261001.md)。D23-A已满足投入条件，下一步准备D23-B完整语义/频率收益门控；A已由用户回传2026-10-01T12:44:35.075903+08:00 COMPLETE，互补诊断均值+1.888456pp，满足准备B门槛；[结果与归档缺口](../experiments/D23_A_COMPLEMENTARITY_RESULTS_20261001.md)。B核心及8项本地CPU合成检查已完成，服务器复验、训练/整图评价入口与资源预检待完成；B正式队列未实现/启动。独立来源验收是外部评价条件，不是所有探索的绝对前置。文档澄清没有新增实验观测或训练授权。

## 最后带时钟的服务器观测：2026-10-01 10:15:16+08:00

Post-D21 原队列 `42/42 COMPLETE`；后续混合退化 C0/C1 四任务队列自动衔接并 `4/4 COMPLETE`、整数审计 `PASS`。10:15 的新观测是服务器逐 tile CPU 审计 `PASS`，结果由用户推送至[诊断 JSON](../../records/post_d21_mixed_followup_compact_20260930/tile_risk_diagnostics.json)。这是历史运行记录，不代表当前 GPU 实时状态。两份 `analysis.json` 均报告 Test6 未加载；[总体开发集结果](../experiments/POST_D21_FINAL_AND_MIXED_FOLLOWUP_RESULTS_20261001.md)及[逐 tile 风险](../experiments/POST_D21_MIXED_TILE_RISK_RESULTS_20261001.md)已记录。原始评价摘要与 checkpoint 仍在服务器，本地没有重新评价影像或哈希 checkpoint 二进制。

研究判断：A 的部分解冻是强基线改进而非 DSM 专属收益；B3 与 C3 未过冻结门槛；D 的联合恢复损失×DSM 交互为负；C1 可学习恢复相对 C0 在固定倍率四块及混合退化八个 pooled 条件均正，但 Vaihingen 局部 tile 退化。tile20 主要见 Car 误报增多，tile33 在未见模糊下见 Building/LowVegetation 漏检与 Tree 误报增多。证据仅限单 seed42、Potsdam Val2 / Vaihingen 同镶嵌图开发区；Test6/独立 final 继续封存；旧Test6已有历史开发暴露，不具诚实独立final资格。当前待办见[可行性判断与条件实验计划](NEXT_EXPERIMENT.md)，本次未启动新训练。旧状态归档于[历史](../history/20261001_before_final_post_d21_results/PROJECT_STATUS.md)。

## 后续准备证据（用户回传）

dfa3456核心8项服务器CPU检查PASS（1.732秒，结束时钟未回传）；A原件已在服务器打包，SHA见[归档观测](../../records/research_d23_a_compact_20261001/server_core_check_and_archive_observation.json)，本地未收到。真实GPU训练crop短测入口已实现，3项本地准入/输出保护检查通过；[短测范围与资源](../protocols/D23_B_CROP_GPU_PROBE_20261001.md)。GPU、整图与正式训练均未执行，旧带时钟A观测仍为12:44:35.075903+08:00。
