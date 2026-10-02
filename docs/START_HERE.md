# START HERE：D27已实际排队，等待D26完成后接力

权威分支rebuild-v1-protocol-20260915，更新2026-10-02。读[研究决定](current/RESEARCH_DECISION.md)→[交接](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)。

最后服务器观测：D27于2026-10-02T23:32:23.937672+08:00为WAITING_D26，controller PID1703686存活，查询时心跳24.6秒、LIVE_WORKERS=[]；D26于2026-10-02T23:32:46.158787+08:00为RUNNING、COMPLETE3/9，九任务终态False、controller锁未释放。查询绝对时间未输出，不能把24.6秒推成精确时间戳。

[排队观测](../records/research_d27_queue_observation_20261002T2332/observation.json)确认新controller正常等待。D27固定执行9e316adc2fa6fd1f2ee0a554d86c9b3f27d1f64c；原D26固定52f94388不改。已有nohup后接实例，不重复启动。九前驱job全部结束且原controller锁释放后，每60秒轮询自动领取GPU0/1；实际接力/新训练尚未观测。

[D27十组协议](protocols/D27_SAFE_ROUTING_PLAN_20261002.md)、[执行说明](protocols/D27_SAFE_ROUTING_EXECUTION_20261002.md)、[固定plan](../records/research_d27_plan_20261002/plan.json)、[验证](../records/research_d27_plan_20261002/local_validation.json)。GPU0/1 H10080GB、RAM/磁盘充足、batch16无累积、nohup、zzx目录是已知约定，不重问资源或重做预算审计。

研究安全融合→专家选择→局部/类别适配；双方信息与退化保留。B0普通融合阶段有益但局部有害，见[复核](experiments/D26_B0_PARTIAL_REVIEW_20261002.md)；本次仅进度，没有新增精度证据。旧D23/D25失败配方关闭，恢复旁支保持；Test6禁读，开发Val2/历史held4不作独立final。


2026-10-03：[实验与2025—2026论文的假设复核](experiments/ASSUMPTIONS_AND_RESEARCH_OPPORTUNITIES_20261003.md)已完成。建议关注相关失效、未知局部不一致与双方信息保留；这是研究建议，不是新增运行或方向变更。先收齐D26/D27结果，再决定有限压力评价。最新服务器状态仍仅上列23:32观测。
