# 当前交接：完整T已分析，26项诊断已登记，15项M完成，最后M运行

最后服务器只读查询（用户终端粘贴，未接收本轮指标原件）：QUERY_OBSERVED=2026-10-11T12:55:27.487901+08:00，queue LAST_OBSERVED=2026-10-11T12:55:15.361980+08:00，RUNNING_M333_context；controller PID3626108 LIVE=True，CPU=COMPLETE，仅GPU0。15/26整项COMPLETE、1项RUNNING、10项PENDING；前15个M已完成并退出，M333_context PID3718262 LIVE=True，phase=inference，tile=3_11，condition=rgb_lines64w8__aux_down4，windows=529/529，progress观测12:55:24.648101，elapsed=158.271144秒，optimizer_updates=0。单tile/条件窗口完成不等于整项完成。L_T0—L_T9尚未启动。这是最后观测，不代表实时状态。

前序已安全交接，原执行cd958925cb5d4292dd15802830e97493c9c67033与原目录research_post_t_mechanism_20261011T094823_3625851保持。所贴nohup日志确认依序完成15个M并启动M333_context，未见本次故障回报；没有精度、R0同源端点或训练轨迹原件，不能判机制成立。新增训练0。回报见[进度摘录](../../records/research_post_t_mechanism_20261011T094823_3625851/user_reported_progress_20261011T125527.json)。

前序检查回报：LAST_OBSERVED=2026-10-11T08:45:44.211597+08:00，TRANSFER_COMPLETE_AWAITING_REVIEW，READY；它确认登记时前序已满足交接检查，不代表新诊断已有完成结果。执行提交cd958925cb5d4292dd15802830e97493c9c67033。登记前CPU检查成功返回由入口链推断，尚未单收服务器cpu_checks.log。

前序最后服务器观测2026-10-11T08:45:44.211597+08:00，TRANSFER_COMPLETE_AWAITING_REVIEW；T0—T9十组全部COMPLETE/8000，CPU完成。快照2026-10-11T09:32:36.322168+08:00，原件379f301f255b9d2348cf11cad79e1374fedd1e7b。此为带时间证据，不是实时服务器查询。

整轮T7=False、U=False、E=False按原门槛保持：T7 RGB_U=83.876407%，相对T1 +0.019790pp、T9随机初始化 +0.059297pp（均逐tile异号），相对T6 +1.453117pp；相对基础+2.863806pp，但比R0=85.001650%低1.125243pp。所有五个上下文匹配对+1.432～+1.521pp且两tile均正；解码器初始化的额外收益未获支持。

POST_T_MECHANISM已登记：16个权重模块包×上下文组合＋10个已有4000步U推理，共26项/296个模型×条件×tile单元/0优化器更新，仅GPU0。执行cd958925，目录research_post_t_mechanism_20261011T094823_3625851，PID3626108；CPU完成，最新观测15/26项完成，M333_context运行，L10待运行。

Potsdam fit12→Val2 3_11/5_10、seed42、fixed8000、native512/stride256、NoBoundary mIoU_fg5。[整轮报告](../experiments/POST_T_FULL_RESULTS_20261011.md)与[冻结后继协议](../protocols/POST_T_MECHANISM_GPU0_20261010.md)。

本次接收原件379f301f、全部T0—T9；核对1774个Git blob清单与95个不同轻量载荷，原计数和固定门槛复算通过，无服务器GPU重现。

继续现有nohup队列，使用原status按需只读观察，不重复enqueue。顺序M16→L10，GPU0单worker、0训练更新。已完成15个M的worker耗时704.836—760.205秒（约11.7—12.7分钟），替代未校准的2—4h估时。12:55时最后M约余9—10分钟；L每项只有4个tile单元，但加载/散列与汇总耗时未测，整队剩余仍须首个L实测校准。不得按条件数线性缩放承诺ETA。失败保留worker/目录后诊断，不自动重试、追加seed或GPU1；完成后上传轻量原件再分析。

执行包源自e106498f，10个Python未改，11项CPU检查/135继承源核验沿用，明确非真实权重GPU试跑。本次同步首项运行观测，不修改服务器代码。

待解：R0整模型表征与只移植解码器之间的差距，是否存在后段学习收益；先诊断，后配对训练。未采纳延长失败配方、T5替代T7、新seed、双向承诺或变更主线。

服务器root仍/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro，前序research_post_s1_transfer_20261010T073327_2852696；原记录保留，只GPU0，nohup，所有产物zzx对应新目录。

[规划前交接原文](../history/HANDOFF_BEFORE_T_FULL_REVIEW_20261011.md)。

[登记前交接原文](../history/HANDOFF_BEFORE_MECHANISM_REGISTRATION_20261011.md)。

[本次进度前交接原文](../history/HANDOFF_BEFORE_MECHANISM_PROGRESS_20261011T095104.md)。
