# 状态与证据接收

最后服务器观测：2026-10-04T20:30:20.922212+08:00，用户粘贴原Post-D30状态：QUEUE=RUNNING、PID2720259、LIVE=True，主体14/18完成。A0—A5/B1—B6保持COMPLETE，C0/C1分别于19:16:14/19:16:05 COMPLETE；C2 GPU1 training step7300/8000、C3 GPU0 step7360/8000，worker均存活；C4 GPU0/C5 GPU1 PENDING。F0—F3仍PENDING，B3 gate=False但实际跳过标记未见。C0/C1仅收到完成状态回报，指标/原始绑定尚未上传验收，不判C2 gate。原状态脚本粗估剩余3.68小时、结束2026-10-05T00:11:12+08:00，非完成承诺。后继最后单独观测仍为20:27:32，PID3029372存活、WAITING_PREDECESSOR，N1四组均未开始，22项条件预约；没有20:30的后继新观测。

固定A2 gate=False：综合对A0+0.101643pp（要求≥+0.2）、对A1−0.044694pp（要求≥+0.2）、对A3−0.023958pp（要求≥+0.1）；其余原生安全/fixed检查通过。固定B3 gate=False：几何对B1+0.021260pp（要求≥+0.5）、对B4−0.012852pp（要求≥+0.2）；DSM锚点正确伤害率较A0增加0.011997pp。F触发条件不成立；不追加A/B种子、追训、扫参或换敏感性最佳组救gate。原C继续。

D23—D28保持已整理结论；D30紧凑原件已收，完整逐tile矩阵未到。Post A/B十二组技术完成，原件上传成功，关键七组整数计数复核PASS；C0/C1已有用户COMPLETE回报、原件待接；C2/C3训练中，C4/C5待运行；F条件False但实际跳过标记未见。

efba23a56eb7f508c0485332cc03c6476bfc8d59上传1769文件，manifest创建18:08:15，原件1899293890字节、上传165121503字节。实际回读plan、portfolio_screen、queue、最新repair_manifest及A0/A1/A2/A3/B1/B3/B4七组complete、selected/fixed8000共14份summary；核对上传与原始SHA、plan/执行绑定和complete的summary SHA，离线核对54432组6×6矩阵tile→pooled及fg5重算、5292组joint汇总和candidate边际一致。A4/A5/B2/B5/B6仅读原生阶段汇总，未逐份验收全部1769文件；未读取服务器权重/预测本体。

上传体积修复服务器成功：165121503字节，低于门禁。修复manifest已收到确认2a15ef与A_optimizer_updates=0。具体口径与结论见[报告](../experiments/POST_D30_AB_RESULTS_20261004.md)。

主线仍RGB–DSM双向条件互补与退化/缺失分割，恢复是旁支，仍处于可行性探索，无确认性新贡献。用户终端操作无SSH，只用GPU0/1两张H10080GB、nohup、seed42/8000步/batch16无累积，全部记录/缓存/快照在zzx对应目录。不重复资源审计，不加seed，不读取Test6/独立final。

## Post-A/B后继条件队列（2026-10-04用户授权）

用户明确要求“按规划进行队列排队吧”。已实现并发布[后继登记与执行协议](../protocols/POST_AB_QUEUE_EXECUTION_20261004.md)：26个训练ID登记，N1四组为可执行首批，其余22组条件预约且执行协议/实现待阶段结果接续。E0只提取已有结果报告，E1待锁定评价条件。登记器先查询原队列，重复登记返回已有目录；nohup等待原18组全部完成、F实际跳过、控制器/worker退出且锁释放，再只用GPU0/1运行N1。首批32000更新，seed42/8000步/batch16，无累积；失败暂停、不自动重试。

N1完成后验整数计数及固定门槛，保存下一匹配基座并停在阶段交接。C2双侧失败会跳过N6。新队列代码/本地CPU8项检查通过，真实权重GPU前向反向尚无服务器执行回报。**已收到服务器登记回报**：执行提交99acf754aaf3f6b1d119f42a5dab7297a263e4b4；目录`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_ab_followup_20261004T185950_3029215`；派生控制器PID3029372；日志`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_ab_followup_20261004T185950_3029215/nohup_20261004T185950714312.log`。登记N1_EXECUTABLE=4、CONDITIONAL_RESERVED=22。20:27用户状态回报确认后继仍存活且WAITING_PREDECESSOR，N1未开始；无需再次登记或恢复。20:30已收到原队列14/18与C2/C3进度，继续正常等待；下一关键动作是原C完成及F跳过后上传稳定快照。原队列结束并释放后自动执行N1四组；N1后其余22项仍待匹配协议/实现，不能声称26项会全部自动运行。

全部代码/日志/缓存在zzx新实验目录；不访问Test6，不重问资源或已给授权。
