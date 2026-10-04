# 共享入口：原C继续，Post-A/B后继条件队列已授权

按[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)→[索引](experiments/rebuild_v1/INDEX.md)读取。权威66322/remote_sensing_frequency的rebuild-v1-protocol-20260915。

最后服务器观测：2026-10-04T20:27:32.472006+08:00，用户粘贴后继状态：QUEUE=WAITING_PREDECESSOR、PID3029372、LIVE=True；N1-0—N1-3均PENDING、step0/8000，N2—N6共22项RESERVED_PROTOCOL_PENDING。最新日志尾40行均为POST_AB_HANDOVER WAITING_PREDECESSOR RUNNING，无本次可见报错。原队列具体C完成计数/步骤仍未更新，本输出不能判断原C训练是否推进或重算完成时间。19:02已见32项条件接口通过；服务器CPU检查按控制流已越过，未独立读取检查日志。原队列细项最后观测18:24，原PID2720259直接存活观测最后为18:59:48。

固定A2 gate=False：综合对A0+0.101643pp（要求≥+0.2）、对A1−0.044694pp（要求≥+0.2）、对A3−0.023958pp（要求≥+0.1）；其余原生安全/fixed检查通过。固定B3 gate=False：几何对B1+0.021260pp（要求≥+0.5）、对B4−0.012852pp（要求≥+0.2）；DSM锚点正确伤害率较A0增加0.011997pp。F触发条件不成立；不追加A/B种子、追训、扫参或换敏感性最佳组救gate。原C继续。

原件efba23a已接收，关键七组14份summary计数及绑定复核PASS，[结果与范围](experiments/POST_D30_AB_RESULTS_20261004.md)。不再要求重复上传A/B；C完成后上传稳定快照。D30完整逐tile矩阵尚未收到。

主线仍RGB–DSM双向条件互补与退化/缺失分割，恢复是旁支，仍处于可行性探索，无确认性新贡献。用户终端操作无SSH，只用GPU0/1两张H10080GB、nohup、seed42/8000步/batch16无累积，全部记录/缓存/快照在zzx对应目录。不重复资源审计，不加seed，不读取Test6/独立final。

## Post-A/B后继条件队列（2026-10-04用户授权）

用户明确要求“按规划进行队列排队吧”。已实现并发布[后继登记与执行协议](protocols/POST_AB_QUEUE_EXECUTION_20261004.md)：26个训练ID登记，N1四组为可执行首批，其余22组条件预约且执行协议/实现待阶段结果接续。E0只提取已有结果报告，E1待锁定评价条件。登记器先查询原队列，重复登记返回已有目录；nohup等待原18组全部完成、F实际跳过、控制器/worker退出且锁释放，再只用GPU0/1运行N1。首批32000更新，seed42/8000步/batch16，无累积；失败暂停、不自动重试。

N1完成后验整数计数及固定门槛，保存下一匹配基座并停在阶段交接。C2双侧失败会跳过N6。新队列代码/本地CPU8项检查通过，真实权重GPU前向反向尚无服务器执行回报。**已收到服务器登记回报**：执行提交99acf754aaf3f6b1d119f42a5dab7297a263e4b4；目录`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_ab_followup_20261004T185950_3029215`；派生控制器PID3029372；日志`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_ab_followup_20261004T185950_3029215/nohup_20261004T185950714312.log`。登记N1_EXECUTABLE=4、CONDITIONAL_RESERVED=22。20:27用户状态回报确认后继仍存活且WAITING_PREDECESSOR，N1未开始；无需再次登记或恢复。下一查询应查看原Post-D30 C阶段具体进度，不能用后继等待日志预测完成时间。原队列结束并释放后自动执行N1四组；N1后其余22项仍待匹配协议/实现，不能声称26项会全部自动运行。

全部代码/日志/缓存在zzx新实验目录；不访问Test6，不重问资源或已给授权。
