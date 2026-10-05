# 共享入口：N1完成，接收原C/N1结果并接续N2协议

最后服务器观测：2026-10-05T07:21:14.003184+08:00（用户粘贴后继状态）。N1-0—N1-3均COMPLETE、8000/8000；QUEUE=N1_COMPLETE_AWAITING_STAGE_PROTOCOL，PID3029372 LIVE=False。控制器按既有协议在N1阶段汇总后正常退出，19项N2—N5仍RESERVED_PROTOCOL_PENDING；N6三项SKIPPED_GATE。日志N1_SCREEN=False：固定N1-3的S_available对N1-1 +2.789491678491075pp，对N1-2 −0.8810586089503829pp。这是用户回报，尚未接收n1_screen及逐tile/计数/完成绑定原件，不声称独立验收通过。原队列日志READY COMPLETE说明后继通过了原18组完成与释放门禁；具体C指标、方向性gate及F实际跳过原件仍待上传，不能仅由N6跳过断言C两方向各自均失败。

[本轮状态、解释与上传命令](experiments/POST_AB_N1_COMPLETION_OBSERVATION_20261005.md)。N2按原规则使用N1-2匹配基座；先验收原件再落实接续，不重启旧控制器。以下10月4日内容为历史记录，若涉及运行态，以本段为最新观测。

## 2026-10-04历史记录与既有科学决定

按[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)→[索引](experiments/rebuild_v1/INDEX.md)读取。权威66322/remote_sensing_frequency的rebuild-v1-protocol-20260915。

最后服务器观测：2026-10-04T20:30:20.922212+08:00，用户粘贴原Post-D30状态：QUEUE=RUNNING、PID2720259、LIVE=True，主体14/18完成。A0—A5/B1—B6保持COMPLETE，C0/C1分别于19:16:14/19:16:05 COMPLETE；C2 GPU1 training step7300/8000、C3 GPU0 step7360/8000，worker均存活；C4 GPU0/C5 GPU1 PENDING。F0—F3仍PENDING，B3 gate=False但实际跳过标记未见。C0/C1仅收到完成状态回报，指标/原始绑定尚未上传验收，不判C2 gate。原状态脚本粗估剩余3.68小时、结束2026-10-05T00:11:12+08:00，非完成承诺。后继最后单独观测仍为20:27:32，PID3029372存活、WAITING_PREDECESSOR，N1四组均未开始，22项条件预约；没有20:30的后继新观测。

固定A2 gate=False：综合对A0+0.101643pp（要求≥+0.2）、对A1−0.044694pp（要求≥+0.2）、对A3−0.023958pp（要求≥+0.1）；其余原生安全/fixed检查通过。固定B3 gate=False：几何对B1+0.021260pp（要求≥+0.5）、对B4−0.012852pp（要求≥+0.2）；DSM锚点正确伤害率较A0增加0.011997pp。F触发条件不成立；不追加A/B种子、追训、扫参或换敏感性最佳组救gate。原C继续。

原件efba23a已接收，关键七组14份summary计数及绑定复核PASS，[结果与范围](experiments/POST_D30_AB_RESULTS_20261004.md)。不再要求重复上传A/B；C完成后上传稳定快照。D30完整逐tile矩阵尚未收到。

主线仍RGB–DSM双向条件互补与退化/缺失分割，恢复是旁支，仍处于可行性探索，无确认性新贡献。用户终端操作无SSH，只用GPU0/1两张H10080GB、nohup、seed42/8000步/batch16无累积，全部记录/缓存/快照在zzx对应目录。不重复资源审计，不加seed，不读取Test6/独立final。

## Post-A/B后继条件队列（2026-10-04用户授权）

用户明确要求“按规划进行队列排队吧”。已实现并发布[后继登记与执行协议](protocols/POST_AB_QUEUE_EXECUTION_20261004.md)：26个训练ID登记，N1四组为可执行首批，其余22组条件预约且执行协议/实现待阶段结果接续。E0只提取已有结果报告，E1待锁定评价条件。登记器先查询原队列，重复登记返回已有目录；nohup等待原18组全部完成、F实际跳过、控制器/worker退出且锁释放，再只用GPU0/1运行N1。首批32000更新，seed42/8000步/batch16，无累积；失败暂停、不自动重试。

N1完成后验整数计数及固定门槛，保存下一匹配基座并停在阶段交接。C2双侧失败会跳过N6。新队列代码/本地CPU8项检查通过，真实权重GPU前向反向尚无服务器执行回报。**已收到服务器登记回报**：执行提交99acf754aaf3f6b1d119f42a5dab7297a263e4b4；目录`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_ab_followup_20261004T185950_3029215`；派生控制器PID3029372；日志`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_ab_followup_20261004T185950_3029215/nohup_20261004T185950714312.log`。登记N1_EXECUTABLE=4、CONDITIONAL_RESERVED=22。20:27用户状态回报确认后继仍存活且WAITING_PREDECESSOR，N1未开始；无需再次登记或恢复。20:30已收到原队列14/18与C2/C3进度，继续正常等待；下一关键动作是原C完成及F跳过后上传稳定快照。原队列结束并释放后自动执行N1四组；N1后其余22项仍待匹配协议/实现，不能声称26项会全部自动运行。

全部代码/日志/缓存在zzx新实验目录；不访问Test6，不重问资源或已给授权。

[记录完整性核对](experiments/GITHUB_RECORD_COMPLETENESS_20261004.md)：已上传清单内未发现漏传，但D30逐tile矩阵与C/F最终原件待接；详见范围和证据边界。本轮用户取消追加N1预检，未发布/安装预检草稿，既有队列不重启。
