# 当前状态：首批15项/96k完成，结果复盘（2026-10-30）

最后完成回执：Full 20:06:07+08；空间20:39:39+08。非实时服务器盘点。

| 范围 | 已收证据 | 结果与边界 |
|---|---|---|
| 原A0 | 2×2k及原14JSON/16矩阵已验 | 内D3+1.6257pp，外−0.6527pp，READY保留 |
| Full B0/B1/G1–3/Q1–3/S1–3 | 11/11 COMPLETE，各8k，总88k，blocked=[] | G/Q/S均未过原实用门槛；原逐tile/边界计数待收 |
| A空间 | 2×2k、校准/outer、四pooled矩阵、缓存/释放回执 | 外层NB fg5 D2=73.7043，D3=70.4069，差−3.2974pp |
| 总预算 | 原A0 4k+Full88k+空间4k | 15项/96k正式更新；profile、旧失败另计 |
| GPU0/1 | 20:37:49空闲快照；20:39:39空间worker释放 | 与首批结束一致，非当前实时存活查询 |
| 条件路线 | A1/A2、C/P/E/F、频率 | 未入队，不自动扩种子 |
| 旧M2/J | 原验收和工程停止沿用 | M2最终清理暂缓，最后确认18端点 |

[复盘及指标口径](../experiments/POST_M2_FIRST_WAVE_COMPLETION_REVIEW_20261030.md)、[用户转录](../../records/post_m2_completion_receipt_20261030/user_pasted_receipt.json)、[空间计数重算](../../records/post_m2_completion_receipt_20261030/count_verification.json)。

本次只读取GitHub和用户回执、保存小证据及更新文档；没有服务器训练/推理/清理/重启。Full512与A组NB128分开解释，F0仅开发、seed42，封存集未开放。
