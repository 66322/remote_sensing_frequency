# 下一步：查询已启动的D24十五组队列

更新2026-10-02 00:19:37（Asia/Shanghai）。最后观测：用户回传队列时间2026-10-02T00:18:59.788679+08:00，QUEUE=RUNNING、COMPLETE=0/15；A0 GPU0 training 2360/4000（00:19:02.780409），A2 GPU1 training 2140/4000（00:19:01.680178），其余13组PENDING。A0第2000步选模后已继续训练；双卡均有持续步数增长，初始化阶段已结束。见[进度证据](../../records/research_d24_progress_20261002T001859/observation.json)。这是用户回传最后观测，不是服务器实时直连；梯度检查原件与新效果指标尚未收到。

实际目录：`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d24_overnight_20261002T000843_877409`。固定执行提交cf1955d966163978b5c8af433f3845b5ca05da9e不变。用户已“按计划进行吧”，[15组科学协议](../protocols/D24_OVERNIGHT_MULTIPERSPECTIVE_20261001.md)和看结果前冻结的预算/阈值不变。[执行说明](../protocols/D24_OVERNIGHT_EXECUTION_20261001.md)保留历史启动方法，但这轮已执行，不重新创建目录。

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
D24_DIR="$PWD/records/research_d24_overnight_20261002T000843_877409"
python -B "$D24_DIR/code/scripts/status_rebuild_v1_d24.py" --directory "$D24_DIR"
tail -n 20 "$D24_DIR/nohup.log"
```

已有双卡持续训练证据；无需再等待首步或另开检查。下一次主要看训练完成后的选模/14条件评价、完成数及是否自动接续A3/A1。A0/A2完成后控制器继续既定15组，每组4000步、合计60000更新，两个H10080GB，物理batch16无累积。按当前普通训练步速，A0/A2训练段在00:19查询时还约6–8分钟，之后有最终选模及14条件评价；不是整轮剩余时间。当前完整job为0，状态工具的known work 0.00h表示可估部分为空，不是马上结束；完整队列ETA待正常完成job后估计。

有TECHNICAL_FAILURE时读对应job log并保留证据，不能当科学负结果；其他组继续，无自动参数扫描/复验。仅控制器确实退出才考虑同目录、同版本恢复，不能凭某次GPU空闲恢复或另开队列。所有快照/缓存/记录保留在该zzx目录；主工作副本不checkout/reset。

完成后自动screen_result.json/results.csv；终端执行轻量上传，支持部分完成或失败证据，长输出从GitHub读取：

```bash
python -B "$D24_DIR/code/scripts/upload_rebuild_v1_d24_records.py" --root "$PWD" --directory "$D24_DIR"
```

上传原计数/选模/配置/绑定/轻量日志；预测/权重仍在服务器并索引。Val2选checkpoint，Test6禁读；单seed开发筛选不能写成确认性贡献，最多两条通过假设另立确认。不重复D23、不自动转向C1。

[当前交接](HANDOFF.md)、[机器计划](../../records/research_d24_overnight_plan_20261001/plan.json)、[本地检查](../../records/research_d24_overnight_plan_20261001/local_validation.json)。
