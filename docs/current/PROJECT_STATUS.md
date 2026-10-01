# 当前状态

更新2026-10-02 00:19:37（Asia/Shanghai）。最后观测：用户回传队列时间2026-10-02T00:18:59.788679+08:00，QUEUE=RUNNING、COMPLETE=0/15；A0 GPU0 training 2360/4000（00:19:02.780409），A2 GPU1 training 2140/4000（00:19:01.680178），其余13组PENDING。A0第2000步选模后已继续训练；双卡均有持续步数增长，初始化阶段已结束。见[进度证据](../../records/research_d24_progress_20261002T001859/observation.json)。这是用户回传最后观测，不是服务器实时直连；梯度检查原件与新效果指标尚未收到。

| 项目 | 状态 |
|---|---|
| 阶段/问题 | 可行性探索；DSM有益融合、负迁移与缺失；贡献未冻结 |
| D23-A | 完成互补性诊断，不是部署收益保证 |
| D23-B | 8/8完成4000步及28/28评价，TS恢复成功 |
| 轻量原件 | GitHub提交6038520；60文件，59索引载荷SHA全部通过 |
| 结果复核 | 3136逐tile、1568pooled矩阵与指标及23冻结判定通过 |
| 科学判定 | TSF未达确认门槛，关闭具体解法；所有学习gate综合低于M0_safe |
| 机制 | 当前S/F增量不足；效用项相对CE减分，同时有减害作用 |
| 下一候选 | D24四角度15组计划定稿：A目标/表示、B类别语义、C光学KD、D增强；代码全部实现、本地15项检查PASS；用户回传A0 training 2360/4000、A2 training 2140/4000，其余13组PENDING，完成0/15 |
| 资源 | GPU0/1，两H10080GB，RAM/磁盘充足；不重做资源审计 |
| 边界 | 单seed42、Potsdam Val2；Test6禁读；权重/预测仍在服务器 |

[完整结果](../experiments/D23_EIGHT_ARM_RESULTS_20261001.md)；[交接](HANDOFF.md)；[下一步](NEXT_EXPERIMENT.md)。

[夜间15组计划](../protocols/D24_OVERNIGHT_MULTIPERSPECTIVE_20261001.md)：15×4000=60000更新，seed42，物理batch16不累积；GPU0/1 nohup，对应zzx独立目录。旧四组草案被本轮计划取代；固定版本cf1955d已由nohup启动，已有目录`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d24_overnight_20261002T000843_877409`；当前只需查询进度，不重复启动或资源审计。
