# 当前交接：Post-D21 两组完成，进入逐 tile 审计

最后带时钟的服务器观测：**2026-10-01 04:53:40+08:00**。原 A/B/C/D 队列 `42/42 COMPLETE`（01:19:17），后续混合退化 C0/C1 队列通过 4/4 smoke、`4/4 COMPLETE` 与整数审计 `PASS`（04:53:40）。新队列确实在原队列完整审计后自动启动。此后未收到服务器实时状态。

[最终开发集分析](../experiments/POST_D21_FINAL_AND_MIXED_FOLLOWUP_RESULTS_20261001.md)已基于用户贴出的两份汇总写入：A 最后四层解冻相对冻结续训约 +3–4 pp，但 DSM 特异性不一致；B3 频率残差、C3 额外恢复监督均未过门槛；D 的恢复损失×DSM 交互在两数据集为负。混合退化 C1−C0 八个 pooled 条件差值均正，但 Vaihingen 多个 tile 下降，最差为 tile33 ×2 未见模糊 −1.421 pp。两份汇总 JSON 已归档，完整逐任务 6×6 整数计数与 checkpoint 仍留服务器，尚未本地独立复算。单 seed42、开发集证据；Test6/独立 final 封存。

下一步：服务器拉取最新 GitHub 分支后，运行 `python -B scripts/analyze_rebuild_v1_mixed_tile_risk.py`。脚本只读取 C0/C1 已有逐 tile 评价摘要，复算计数和现有差值，生成小型 `tile_risk_diagnostics.json`；详见[协议](../protocols/POST_D21_MIXED_TILE_RISK_AUDIT_20261001.md)。检查 Vaihingen tile20/33 与 Potsdam `5_10` 的逐类计数、边界和恢复诊断后，再决定是否冻结确认性实验或独立来源验证；当前没有自动追加 GPU 训练、下载或多种子任务。上一版交接归档于 [历史](../history/20261001_before_final_post_d21_results/HANDOFF.md)。
