# 共享入口（2026-10-04交接整理）

权威为66322/remote_sensing_frequency的rebuild-v1-protocol-20260915，两台电脑以GitHub同步。本次为记录整理，不启动服务器任务。

按顺序读[研究决定](current/RESEARCH_DECISION.md)→[当前交接](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)→[实验总索引](experiments/rebuild_v1/INDEX.md)。[新对话可直接使用的说明](current/NEW_CHAT_HANDOFF_20261004.md)。

最后服务器观测：2026-10-04T17:21:47.568226+08:00（用户终端查询回传），Post-D30为RUNNING，控制器2720259 LIVE=True，主体12/18完成：A0—A5、B1—B6全部COMPLETE；C0在GPU0训练3760/8000步，C1在GPU1训练3780/8000步，两worker PID_LIVE=True；C2—C5 PENDING，F0—F3仍有条件。原队列已进入C，禁止重复恢复或新建队列。旧08:12日志的model导入错误仅作历史记录。本次仍未收到上传提交，GitHub没有新增A/B原生结果；固定A2/B3门槛尚待原件分析，不能由技术完成判定科学成立。

主问题保持RGB外观/语义与DSM高度/几何的双向条件互补，及任一侧退化/缺失时的分割能力。仍处于可行性探索；频率、可靠性、MoE、共享/私有是候选解法，任务驱动SR/恢复是旁支，不因任务顺序改变主线。普通融合、部分解冻与增强是强基线；旧机制未过门槛不等于整个问题失败。目前没有确认性新贡献。

服务器由用户在终端操作，无可用SSH。根目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro；只用物理GPU0/1，两张H10080GB，RAM/磁盘充足。长任务nohup；记录、临时、缓存、执行快照均在/home/jovyan/zzx对应实验目录。当前协议seed42、8000步、物理batch16、无累积。不重复资源审计、容量探针、单模态训练或自动追加多seed。Test6/独立final禁止访问；Val2重复开发，不称独立确认。

D23—D28已完成分析；D30已完成六项且紧凑原件已上传；A六项完成但原生结果待接收。不同轮预算、选模与综合定义不同，不跨表排名次。详见[完成实验整理](experiments/COMPLETED_EXPERIMENTS_HANDOFF_20261004.md)。权重/预测仍在服务器；D30全逐tile矩阵尚未上传。
