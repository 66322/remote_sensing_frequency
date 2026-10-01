# 下一步：查询已启动的D24十五组队列

更新2026-10-02 00:15:45（Asia/Shanghai）。最后服务器观测来源为用户回传启动输出（目录创建时间2026-10-02 00:08:43 +08:00，由目录名推得；日志无精确观测时间）：GPU0 A0 pid=1003559、GPU1 A2 pid=1003563，均initializing step=0。已由nohup启动双卡队列，但首步TRAIN/gradient_check未收到；无D24 traceback。PID是历史观测，不是实时存活证明；未收到nvidia-smi数值。见[启动证据](../../records/research_d24_launch_observation_20261002/user_reported_launch.json)。

实际目录：`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d24_overnight_20261002T000843_877409`。固定执行提交cf1955d966163978b5c8af433f3845b5ca05da9e不变。用户已“按计划进行吧”，[15组科学协议](../protocols/D24_OVERNIGHT_MULTIPERSPECTIVE_20261001.md)和看结果前冻结的预算/阈值不变。[执行说明](../protocols/D24_OVERNIGHT_EXECUTION_20261001.md)保留历史启动方法，但这轮已执行，不重新创建目录。

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
D24_DIR="$PWD/records/research_d24_overnight_20261002T000843_877409"
python -B "$D24_DIR/code/scripts/status_rebuild_v1_d24.py" --directory "$D24_DIR"
tail -n 20 "$D24_DIR/nohup.log"
```

先看phase、step、progress_at及最后记录时间。加载权重/12个fit tile后出现TRAIN；首步gradient_check是运行中的必要梯度检查，不是另开资源/预算探针。A0/A2完成后控制器继续既定15组，每组4000步、合计60000更新，两个H10080GB，物理batch16无累积。结束时间只利用正常已完成job近似估计；当前没有足够耗时证据，不承诺明早结束。

有TECHNICAL_FAILURE时读对应job log并保留证据，不能当科学负结果；其他组继续，无自动参数扫描/复验。仅控制器确实退出才考虑同目录、同版本恢复，不能凭某次GPU空闲恢复或另开队列。所有快照/缓存/记录保留在该zzx目录；主工作副本不checkout/reset。

完成后自动screen_result.json/results.csv；终端执行轻量上传，支持部分完成或失败证据，长输出从GitHub读取：

```bash
python -B "$D24_DIR/code/scripts/upload_rebuild_v1_d24_records.py" --root "$PWD" --directory "$D24_DIR"
```

上传原计数/选模/配置/绑定/轻量日志；预测/权重仍在服务器并索引。Val2选checkpoint，Test6禁读；单seed开发筛选不能写成确认性贡献，最多两条通过假设另立确认。不重复D23、不自动转向C1。

[当前交接](HANDOFF.md)、[机器计划](../../records/research_d24_overnight_plan_20261001/plan.json)、[本地检查](../../records/research_d24_overnight_plan_20261001/local_validation.json)。
