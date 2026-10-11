# 研究决定：诊断完成，先验原件后冻结配对训练

权威共享源：66322/remote_sensing_frequency，rebuild-v1-protocol-20260915；本地仅工作副本。

最后服务器查询（用户粘贴终端回报）：QUERY_OBSERVED=2026-10-11T13:48:26.474610+08:00；queue LAST_OBSERVED=2026-10-11T13:42:45.195415+08:00，MECHANISM_COMPLETE_AWAITING_REVIEW。CPU完成，M16＋L10全部26项COMPLETE；查询时controller PID3626108及全部worker LIVE=False，仅GPU0，NEW_OPTIMIZER_UPDATES=0。nohup完整派发/完成并NO_FURTHER_DISPATCH，未见本次故障回报。这是最后观测，不代表新的实时查询。

服务器DIAGNOSTIC_SCREEN回报matched_budget_study_supported=True、representation_followup_signal=True；next_training_launched=False、automatic_retry=False。此为未独立验收的汇总回报，未收到本轮精度、原计数、checkpoint绑定或R0同源端点原件；不能判新方法有效或把信号当作双向贡献。来源：[完成回报](../../records/research_post_t_mechanism_20261011T094823_3625851/user_reported_completion_20261011T134826.json)。

执行提交cd958925cb5d4292dd15802830e97493c9c67033保持，目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_t_mechanism_20261011T094823_3625851。M333_context完成观测13:04:28；L十项worker实测206.411—210.024秒/项，最后L_T9完成观测13:42:23。旧剩余估时已失效。

研究阶段仍为可行性探索与机制定位。主线RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复为旁支；当前已验证线索偏RGB已知局部缺失。

完整T0—T9原件379f301f已完成此前离线验收；Potsdam fit12→Val2=3_11/5_10、seed42、fixed8000、native512/stride256、NoBoundary mIoU_fg5。T7 RGB_U=83.876407%，比R0=85.001650%低1.125243pp；五上下文匹配对+1.432—1.521pp且两tile正。原T7/U/E gate均False，解码器初始化额外收益未获支持。旧gate不变，不后验改选T5或扩大旧配方预算。

[完整T报告](../experiments/POST_T_FULL_RESULTS_20261011.md)、[冻结诊断协议](../protocols/POST_T_MECHANISM_GPU0_20261010.md)。当前26项是推理诊断，无新训练；完成不自动启动下一轮。

立即下一步：在用户服务器终端用原目录code/scripts/upload_post_t_mechanism_records.py --root ROOT --directory DIR显式上传轻量原件，无需再次登记或启动。仅上传轻量JSON/计数/配置/代码/日志及服务器大文件索引，权重和预测数组保留原目录；用户返回上传提交号后助手从GitHub回读。

先核验清单/无损解码SHA、26项完成与执行绑定、M333_context对全部16个R0 case逐像素同源端点、int64 6×6计数及tile→pooled；再复算固定模块配对与全部因素配对、保护底线、0→4000→8000 RGB_U/DSM_U轨迹和4000 checkpoint绑定。未校准交换负结果不能证明信息缺失。

原件通过后，依据专家包信号与T1/T7固定后段信号制定真正的配对训练协议：明确待训练参数、同预算普通控制、冻结/简单解冻/容量控制、主指标、保护与停止门槛及学习率日程。下一轮尚未定型、未登记、未启动；不直接续跑已衰减到零的8000步日程救旧gate。

服务器由用户执行、无SSH；仅GPU0，不访问Test6/held4/final，不自动重跑失败配方、加seed或GPU1。所有记录/执行快照/归档在/home/jovyan/zzx对应目录。重要结论与交接继续写同一GitHub分支并回读。

决定及来源：用户10月11日要求先查询原队列、接收核验轻量原件，再分析模块与轨迹并制定配对训练。未采纳重跑失败配方、增加种子、扩预算救旧gate或更改研究主线。下一不确定性为同源端点与固定信号能否独立复算，及何种适应机制值得同预算训练。
