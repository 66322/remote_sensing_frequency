# 下一步：独立来源验收与 C1 成对评价

原 42 项与后续 4 项均已完成，逐 tile 审计 `PASS`；见[总体结果](../experiments/POST_D21_FINAL_AND_MIXED_FOLLOWUP_RESULTS_20261001.md)和[局部风险结果](../experiments/POST_D21_MIXED_TILE_RISK_RESULTS_20261001.md)。C1 的八个 pooled 开发条件为正，但 Vaihingen tile20 Car 误报增多、tile33 在未见模糊下 Building/LowVegetation 漏检增多且 Tree 误报增多。当前不追加训练。

下一门禁是独立地理来源验收：明确公开来源与许可、RGB/标签类别映射、地理/影像配准、无训练重叠、文件大小与 SHA、服务器访问路线和空间/内存需求。**通过验收后**用冻结的 C0/C1 checkpoint 对新地区做一次成对评价，仍分开报告 ×2/×4 clean 与预设未见模糊、pooled/逐 tile/逐类计数，不用新地区选模。类别定义不完全一致时只报可比类别分项，不沿用原 fg5 汇总口径。若短期没有可接受数据，另行预注册容量匹配前端对照，先实现与吞吐审计，再决定是否用单 seed42 做探索训练。不得用 Test6、补第三种子或开发集反复调参消除既有失败门槛；完整评价产物仍在服务器，上一版下一步见[历史](../history/20261001_before_final_post_d21_results/NEXT_EXPERIMENT.md)。
