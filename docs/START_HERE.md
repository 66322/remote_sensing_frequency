# 共享入口（2026-10-04交接整理）

权威为66322/remote_sensing_frequency的rebuild-v1-protocol-20260915，两台电脑以GitHub同步。本次为记录整理，不启动服务器任务。

按顺序读[研究决定](current/RESEARCH_DECISION.md)→[当前交接](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)→[实验总索引](experiments/rebuild_v1/INDEX.md)。[新对话可直接使用的说明](current/NEW_CHAT_HANDOFF_20261004.md)。

最后服务器观测：2026-10-04T08:41:43.586227+08:00，Post-D30为CONTROLLER_INTERRUPTED，控制器2698383已退出；A0—A5六项COMPLETE，B1—B6/C0—C5待运行，F0—F3有条件。无活跃worker是该时刻的观测，不代表此刻状态。A评价修复已成功，无新增优化器更新；随后A阶段汇总因缺少model导入路径退出。第二次修复2a15ef163c3df7e96ee52c81cb677ebdb1305935已发布并通过本地6项回归，但尚无服务器启动回报。

主问题保持RGB外观/语义与DSM高度/几何的双向条件互补，及任一侧退化/缺失时的分割能力。仍处于可行性探索；频率、可靠性、MoE、共享/私有是候选解法，任务驱动SR/恢复是旁支，不因任务顺序改变主线。普通融合、部分解冻与增强是强基线；旧机制未过门槛不等于整个问题失败。目前没有确认性新贡献。

服务器由用户在终端操作，无可用SSH。根目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro；只用物理GPU0/1，两张H10080GB，RAM/磁盘充足。长任务nohup；记录、临时、缓存、执行快照均在/home/jovyan/zzx对应实验目录。当前协议seed42、8000步、物理batch16、无累积。不重复资源审计、容量探针、单模态训练或自动追加多seed。Test6/独立final禁止访问；Val2重复开发，不称独立确认。

D23—D28已完成分析；D30已完成六项且紧凑原件已上传；A六项完成但原生结果待接收。不同轮预算、选模与综合定义不同，不跨表排名次。详见[完成实验整理](experiments/COMPLETED_EXPERIMENTS_HANDOFF_20261004.md)。权重/预测仍在服务器；D30全逐tile矩阵尚未上传。
