# 下一步：查询已有D26/D27，等待自动接力

最后服务器观测：D27于2026-10-02T23:32:23.937672+08:00为WAITING_D26，controller PID1703686存活，查询时心跳24.6秒、LIVE_WORKERS=[]；D26于2026-10-02T23:32:46.158787+08:00为RUNNING、COMPLETE3/9，九任务终态False、controller锁未释放。查询绝对时间未输出，不能把24.6秒推成精确时间戳。

D27实际排队已确认，正常nohup等待，当前执行范围为原D26九组→新D27十组，不需再次启动或切换。九原job结束且controller锁释放，D27在下一轮60秒检查后开始领取GPU0/1。若原controller中断而worker仍活着，先诊断原队列，不创建第二个后接controller。

查询后接进度：
```bash
D27_DIR=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d27_safe_routing_after_d26_20261002T191253_1513109
python -B "$D27_DIR/code/scripts/status_rebuild_v1_d27.py" --directory "$D27_DIR"
python -B "$D27_DIR/check_handover_2e7a678.py" --directory "$D27_DIR"
```

D27_WAITING_D26为等待；D27_PREDECESSOR_FINISHED/D27_STARTED为接力启动；D27_TRAIN和step>0才证明训练推进。只读诊断确认PID/心跳/锁，不测资源预算。

两轮完成或失败后，各用自身code/scripts/upload_rebuild_v1_d26_records.py或upload_rebuild_v1_d27_records.py --root工程根目录 --directory对应目录，把原轻量评价/矩阵/日志/绑定写回GitHub，weights/predictions留服务器索引。按原D26/D27各自冻结gate判断，不自动追训/扫参或访问Test6。[当前观测](../../records/research_d27_queue_observation_20261002T2332/observation.json)不代表全量运行产物已归档。


## 完整结果后的候选，尚未排队

[假设复核及有限下一步设计](../experiments/ASSUMPTIONS_AND_RESEARCH_OPPORTUNITIES_20261003.md)建议先复用D26/D27原矩阵，再以原选模checkpoint比较同边际、不同错误相关性。首批候选6模型×8条件×2开发tile，不训练，不资源探针；具体幅度/随机实现/门槛另立执行协议后才能运行。该建议不替代现有冻结gate，不自动追加第三队列。只有现象成立才做增强×机制2×2训练；强简单对照解释全部收益则停止复杂机制。不可将报告建议写成已授权新运行。
