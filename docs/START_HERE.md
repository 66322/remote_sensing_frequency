# 共享入口：A/B已收且gate失败，原C继续

按[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)→[索引](experiments/rebuild_v1/INDEX.md)读取。权威66322/remote_sensing_frequency的rebuild-v1-protocol-20260915。

最后服务器记录快照：2026-10-04T18:07:21.987874+08:00，queue_status=RUNNING，主体12/18完成，A0—A5及B1—B6 COMPLETE；C0/C1在GPU0/1训练至8000步，phase=checkpoint_selection，尚非COMPLETE；C2—C5 PENDING，F仍PENDING。该快照未新查PID存活；最近存活证据为17:21用户查询。不把18:08上传时间当运行完成时间。

固定A2 gate=False：综合对A0+0.101643pp（要求≥+0.2）、对A1−0.044694pp（要求≥+0.2）、对A3−0.023958pp（要求≥+0.1）；其余原生安全/fixed检查通过。固定B3 gate=False：几何对B1+0.021260pp（要求≥+0.5）、对B4−0.012852pp（要求≥+0.2）；DSM锚点正确伤害率较A0增加0.011997pp。F触发条件不成立；不追加A/B种子、追训、扫参或换敏感性最佳组救gate。原C继续。

原件efba23a已接收，关键七组14份summary计数及绑定复核PASS，[结果与范围](experiments/POST_D30_AB_RESULTS_20261004.md)。不再要求重复上传A/B；C完成后上传稳定快照。D30完整逐tile矩阵尚未收到。

主线仍RGB–DSM双向条件互补与退化/缺失分割，恢复是旁支，仍处于可行性探索，无确认性新贡献。用户终端操作无SSH，只用GPU0/1两张H10080GB、nohup、seed42/8000步/batch16无累积，全部记录/缓存/快照在zzx对应目录。不重复资源审计，不加seed，不读取Test6/独立final。
