# 下一步：上传D24完成证据并分析匹配对照

更新2026-10-02 12:10:21（Asia/Shanghai）。最后观测：用户回传队列记录2026-10-02T04:06:59.332637+08:00，COMPLETE 15/15；所有组4000/4000，最后B3完成标记04:06:53.704712，汇总summary_exit=0、test6_loaded=False。见[完成观测](../../records/research_d24_completion_observation_20261002/observation.json)。已收到15组四位小数指标；完整screen_result、逐tile/条件原计数、选模绑定与梯度检查尚未上传/复核。查询显示的12:09 ROUGH_QUEUE_END是查询时间加零剩余，不是实际完成时间。

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
D24_DIR="$PWD/records/research_d24_overnight_20261002T000843_877409"
python -B "$D24_DIR/code/scripts/upload_rebuild_v1_d24_records.py" --root "$PWD" --directory "$D24_DIR"
```

上传器复用本次快照，不启动训练；将screen_result.json、results.csv、15组评价原计数/逐tile/条件/风险/缺失记录、选模/checkpoint绑定、gradient_check、轻量日志及产物索引写回同一分支。Git凭据在终端交互；预测/权重留服务器。全部上传准备文件也在本次zzx目录。

贴回提交与记录链接后读取完整原件：先确认manifest与绑定，再重算配对差值、原矩阵/pooled和冻结screen；分开报告部分解冻强基线、普通增强、Pair、同容量原型、区域KD。每组训练完成不等于机制通过。不得从打印榜单追训赢家或新增扫描。

初步综合信号：A2-A0约+2.9868pp；Pair和类别原型近零；类别平衡明显减分；C2低于C0；D1-D0约+0.5791pp且D1打印最高。完整精度/风险约束未收到，不决定确认候选，不改主线、阈值或最终贡献承诺。最多两条通过假设再单独规划确认。

[科学协议](../protocols/D24_OVERNIGHT_MULTIPERSPECTIVE_20261001.md)、[执行说明](../protocols/D24_OVERNIGHT_EXECUTION_20261001.md)、[当前交接](HANDOFF.md)。
