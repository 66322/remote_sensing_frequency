> 历史快照，来自1a8a840；其中下一步安排已由当前研究定位澄清替代，不作为当前执行指令。

# 当前项目状态

## 最后带时钟的服务器观测：2026-10-01 10:15:16+08:00

Post-D21 原队列 `42/42 COMPLETE`；后续混合退化 C0/C1 四任务队列自动衔接并 `4/4 COMPLETE`、整数审计 `PASS`。10:15 的新观测是服务器逐 tile CPU 审计 `PASS`，结果由用户推送至[诊断 JSON](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/records/post_d21_mixed_followup_compact_20260930/tile_risk_diagnostics.json)。这是历史运行记录，不代表当前 GPU 实时状态。两份 `analysis.json` 均报告 Test6 未加载；[总体开发集结果](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/experiments/POST_D21_FINAL_AND_MIXED_FOLLOWUP_RESULTS_20261001.md)及[逐 tile 风险](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/experiments/POST_D21_MIXED_TILE_RISK_RESULTS_20261001.md)已记录。原始评价摘要与 checkpoint 仍在服务器，本地没有重新评价影像或哈希 checkpoint 二进制。

研究判断：A 的部分解冻是强基线改进而非 DSM 专属收益；B3 与 C3 未过冻结门槛；D 的联合恢复损失×DSM 交互为负；C1 可学习恢复相对 C0 在固定倍率四块及混合退化八个 pooled 条件均正，但 Vaihingen 局部 tile 退化。tile20 主要见 Car 误报增多，tile33 在未见模糊下见 Building/LowVegetation 漏检与 Tree 误报增多。证据仅限单 seed42、Potsdam Val2 / Vaihingen 同镶嵌图开发区；Test6/独立 final 继续封存。下一门禁为[独立来源验收与成对评价](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/current/NEXT_EXPERIMENT.md)，暂无新训练队列。旧状态归档于[历史](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/history/20261001_before_final_post_d21_results/PROJECT_STATUS.md)。
