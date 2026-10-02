# 当前交接：D27实际后台排队已确认

更新2026-10-02。研究仍可行性探索，主问题安全融合→动态专家→局部/类别适配，双方信息与退化/缺失保留。最终贡献未冻结。用户已授权十组后接执行。

最后服务器观测：D27于2026-10-02T23:32:23.937672+08:00为WAITING_D26，controller PID1703686存活，查询时心跳24.6秒、LIVE_WORKERS=[]；D26于2026-10-02T23:32:46.158787+08:00为RUNNING、COMPLETE3/9，九任务终态False、controller锁未释放。查询绝对时间未输出，不能把24.6秒推成精确时间戳。

[只读诊断观测](../../records/research_d27_queue_observation_20261002T2332/observation.json)、[用户回传原输出](../../records/research_d27_queue_observation_20261002T2332/user_diagnostic_stdout.txt)支持ACTIVE_QUEUED_WAITING_PREDECESSOR。此前“未观测启动”仅历史阶段，当前新等待controller确实运行；D27训练/实际接力尚未发生。此为运行证据，没有新精度/频率/语义贡献。

固定D27执行9e316adc2fa6fd1f2ee0a554d86c9b3f27d1f64c，独立目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d27_safe_routing_after_d26_20261002T191253_1513109，日志nohup_20261002T232423_1703136.log。固定D26执行52f94388b1a9c7557e9ef533075661139cd55eda，原目录research_d26_bidirectional_20261002T191253_1513109。只获总完成3/9，未获本次逐job身份及新评价指标，不推测谁完成。

接力条件：原九job终态+原controller锁释放，D27每60秒轮询，随后动态GPU0/1领任务；设备仍有其他存活进程则等待。预期接力已配置且等待controller存活，不等于实际接力已验证。用户可正常断开终端，既有nohup继续；当前只查询已排队实例，不重新启动。

十组S0/S1/G0/G1/L0/L1/C0/C1/L1-sh/C1-sh各8000，G0/G1先跑，80k总更新、batch16无累积。[协议](../protocols/D27_SAFE_ROUTING_PLAN_20261002.md)、[执行说明](../protocols/D27_SAFE_ROUTING_EXECUTION_20261002.md)、[固定plan](../../records/research_d27_plan_20261002/plan.json)。14CPU+30文件自包含/五入口检查通过；CPU不代表CUDA精度。冻结原单模态anchors、三个轻量残差专家、路由×CE/保护恢复与打乱，已知缺失结构回退，新增24条件包含2项present-DSM诊断，不改选模。

后续从已有目录status脚本查询进度或check_handover_2e7a678.py复核PID/心跳/锁；结束后两轮各用原上传脚本同步长轻量原件。原D26旧门槛不改；D27按自己的对照/去留，最多一条另立确认。只读诊断和状态证明不重启资源审计、不扩大budget。

资源GPU0/1 H10080GB，RAM/磁盘充足，nohup和zzx对应目录约定不再询问。服务器由用户操作，无SSH。D23/D25具体失败配方关闭，恢复C1旁支不升级（D27:C1只是类别任务id）。频率待独立增量，STARS补偿另立；GLFRNet原文未核验。不读Test6，Val2/历史held4不作独立final。GitHub为共享事实源，本观测不意味着全服务器日志/weights/predictions已上传。
