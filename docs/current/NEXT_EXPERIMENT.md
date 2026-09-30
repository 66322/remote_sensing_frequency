# 下一步：完成原 D 组，同时准备混合退化配对实验

最后观测 2026-09-30 23:41:41+08:00：原42项队列只剩D最后两项在运行，等待0。无需为提前分析强杀这两项；A/B/C 阶段结果已[记录](../experiments/POST_D21_EARLY_AB_C_RESULTS_20260930.md)。新[四任务 C0/C1 混合退化组](../protocols/POST_D21_MIXED_DEGRADATION_FOLLOWUP_20260930.md)可先做服务器准备并后台等待原队列完成，原队列若 INCOMPLETE 则新组不会启动。新组只比较可学习恢复的退化泛化，不补 B3/C3 种子。

新组首次等待器因补强最终审计门禁，已通过独立 `STOP` 在训练前退出。下一步拉取修正版，单独运行 `python -B scripts/run_rebuild_v1_mixed_followup.py --prepare-only`，确认未启动计划归档，然后移除 `records/post_d21_mixed_followup_queue_20260930/STOP`，重启新组后台等待器。不得向原队列写 STOP。若原队列最终审计不是 42/42 PASS，新组必须保持未启动并先诊断。
