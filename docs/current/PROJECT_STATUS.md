# 项目状态：T十组验收完成，GPU0诊断后继已登记，进度待查询

最新服务器登记回报（用户终端，2026-10-11）：MECHANISM_QUEUE_REGISTERED，目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_t_mechanism_20261011T094823_3625851，controller PID3626108，GPU=0 ONLY，DIAGNOSTIC_JOBS=26，NEW_STEPS=0；日志nohup_20261011T094831668881.log。目录09:48:23、日志09:48:31.668881为命名时间标记，不是queue observed_at。当前REGISTERED_PROGRESS_NOT_YET_QUERIED，尚无controller/worker存活、CPU准备或CUDA首项进度回报。

前序检查回报：LAST_OBSERVED=2026-10-11T08:45:44.211597+08:00，TRANSFER_COMPLETE_AWAITING_REVIEW，READY；它确认登记时前序已满足交接检查，不代表新诊断已有完成结果。执行提交cd958925cb5d4292dd15802830e97493c9c67033。登记前CPU检查成功返回由入口链推断，尚未单收服务器cpu_checks.log。

前序最后服务器观测2026-10-11T08:45:44.211597+08:00，TRANSFER_COMPLETE_AWAITING_REVIEW；T0—T9十组全部COMPLETE/8000，CPU完成。快照2026-10-11T09:32:36.322168+08:00，原件379f301f255b9d2348cf11cad79e1374fedd1e7b。此为带时间证据，不是实时服务器查询。

整轮T7=False、U=False、E=False按原门槛保持：T7 RGB_U=83.876407%，相对T1 +0.019790pp、T9随机初始化 +0.059297pp（均逐tile异号），相对T6 +1.453117pp；相对基础+2.863806pp，但比R0=85.001650%低1.125243pp。所有五个上下文匹配对+1.432～+1.521pp且两tile均正；解码器初始化的额外收益未获支持。

POST_T_MECHANISM已登记：16个权重模块包×上下文组合＋10个已有4000步U推理，共26项/296个模型×条件×tile单元/0优化器更新，仅GPU0。执行cd958925，目录research_post_t_mechanism_20261011T094823_3625851，PID3626108；新运行进度尚未查询。

Potsdam fit12→Val2 3_11/5_10、seed42、fixed8000、native512/stride256、NoBoundary mIoU_fg5。[整轮报告](../experiments/POST_T_FULL_RESULTS_20261011.md)与[冻结后继协议](../protocols/POST_T_MECHANISM_GPU0_20261010.md)。

下一步只读新目录code/scripts/status_post_t_mechanism.py以及nohup/preparation日志，确认CPU准备、controller存活及首个M任务；不要重复enqueue或重启T。26项自动串行、仅GPU0、0训练更新，预计接手后2—4h为粗范围，尚待首项校准。失败时保留目录/worker并诊断，不自动重试。结束上传轻量原件，再定后续训练。
