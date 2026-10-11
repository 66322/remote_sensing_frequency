# 研究决定：关闭解码初始化增量承诺，继续定位上下文能力差距

最后服务器只读查询（用户终端）：QUERY_OBSERVED=2026-10-11T09:51:04.266613+08:00，queue LAST_OBSERVED=2026-10-11T09:50:54.789468+08:00，RUNNING_M000_masked；controller PID3626108 LIVE=True，CPU=COMPLETE，仅GPU0。首项M000_masked PID3626555 LIVE=True，phase=inference，tile=3_11，condition=dsm_U，windows=529/529，progress观测09:50:47.640628，elapsed=81.824804秒，optimizer_updates=0。

前序已安全交接：READY、controller_live=False、workers_live=False，checked_at=2026-10-11T09:48:31.724509+08:00；原T最后观测08:45:44.211597。当前0/26整项完成、1项运行、25项PENDING；529/529仅为单tile单条件窗口进度，不代表整个M项或队列完成。暂无新精度/R0端点/机制结论，也无本次故障回报。

前序检查回报：LAST_OBSERVED=2026-10-11T08:45:44.211597+08:00，TRANSFER_COMPLETE_AWAITING_REVIEW，READY；它确认登记时前序已满足交接检查，不代表新诊断已有完成结果。执行提交cd958925cb5d4292dd15802830e97493c9c67033。登记前CPU检查成功返回由入口链推断，尚未单收服务器cpu_checks.log。

前序最后服务器观测2026-10-11T08:45:44.211597+08:00，TRANSFER_COMPLETE_AWAITING_REVIEW；T0—T9十组全部COMPLETE/8000，CPU完成。快照2026-10-11T09:32:36.322168+08:00，原件379f301f255b9d2348cf11cad79e1374fedd1e7b。此为带时间证据，不是实时服务器查询。

整轮T7=False、U=False、E=False按原门槛保持：T7 RGB_U=83.876407%，相对T1 +0.019790pp、T9随机初始化 +0.059297pp（均逐tile异号），相对T6 +1.453117pp；相对基础+2.863806pp，但比R0=85.001650%低1.125243pp。所有五个上下文匹配对+1.432～+1.521pp且两tile均正；解码器初始化的额外收益未获支持。

POST_T_MECHANISM已登记：16个权重模块包×上下文组合＋10个已有4000步U推理，共26项/296个模型×条件×tile单元/0优化器更新，仅GPU0。执行cd958925，目录research_post_t_mechanism_20261011T094823_3625851，PID3626108；CPU准备完成、首项GPU0推理已确认，尚无整项完成。

Potsdam fit12→Val2 3_11/5_10、seed42、fixed8000、native512/stride256、NoBoundary mIoU_fg5。[整轮报告](../experiments/POST_T_FULL_RESULTS_20261011.md)与[冻结后继协议](../protocols/POST_T_MECHANISM_GPU0_20261010.md)。

研究阶段：可行性探索与机制定位。主问题仍RGB–DSM双向条件互补与退化/缺失分割；任务驱动恢复为旁支，当前证据仅偏RGB局部缺失。

决定及来源：用户10月10—11日授权规划并自动接续，后要求结合完整T；本次379f301f原件验收后保留26项诊断。没有改选T5、重跑T7、加seed或扩大预算；不会从解码配方失败推出问题不成立。

下一不确定性：R0差距来自哪类专家/解码模块与上下文组合，T目标指标后段是否仍明显改善。未校准模块交换负结果只能说明组合未成立，不证明信息不存在。固定轨迹和模块信号均仅决定后续配对训练设计，不改旧gate。
