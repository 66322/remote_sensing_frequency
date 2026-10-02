# Start Here

共享记录权威：66322/remote_sensing_frequency的rebuild-v1-protocol-20260915分支。1a8a840是历史基准，不是最新执行版本；不能以另一台电脑的旧本地交接覆盖远端。

**已明确资源：GPU0、GPU1，两张H100 80GB，RAM/硬盘充足；长实验nohup，所有产物在/home/jovyan/zzx对应目录。新对话复用已完成验收，不从资源审计重新开始。**

先读本页，再依次读：

1. [研究决策](current/RESEARCH_DECISION.md)：问题主线、候选角色、决定来源和证据边界。
2. [当前交接](current/HANDOFF.md)：最后观测、执行绑定及立即工作。
3. [当前状态](current/PROJECT_STATUS.md)：简要阶段表，不把旧PID当实时状态。
4. [下一步](current/NEXT_EXPERIMENT.md)：接续既定任务，再定稿下一假设。

当前为可行性探索，主问题仍是光学可用时DSM有益融合、负迁移及缺失能力。D23当前TSF解法关闭；D24十五组已完成并上传acd2dbf，见[完整复核与Pair纠错](experiments/D24_REVIEW_AND_PAIR_CORRECTION_20261002.md)。A1/A3因开关大小写错误未启用Pair，必须撤回Pair无效判断；其他比较支持部分解冻/增强强基线，以及完整与缺失精度的取舍。基于[近期原论文](literature/D25_OPTIMIZATION_AND_MISSINGNESS_20261002.md)，下一建议是[D25八组机制检验](protocols/D25_MISSINGNESS_OPTIMIZATION_PLAN_20261002.md)，尚未实现/启动。直接接续实现，不重跑D23/D24或资源审计；C1恢复仍旁支，最终解法/章节未冻结。

用户新增要求：实质新实验须参考近期原论文并明确借鉴、差异、假设和对照。已完成[2025—2026文献映射](literature/RECENT_MULTIMODAL_SEGMENTATION_20261001.md)，按[文献到实验规则](protocols/LITERATURE_TO_EXPERIMENT.md)复用，不为每次接续重查或阻塞既定训练。

按需核对[长期执行约定](protocols/EXECUTION_CONTRACT.md)、[不可重复事项](current/DO_NOT_REPEAT.md)、[机器台账](../records/rebuild_v1_experiment_registry.json)、[实验索引](experiments/rebuild_v1/INDEX.md)、[共享记录规则](protocols/RECORD_SOURCE_AND_HANDOFF.md)。只读已有证据不等于重跑审计。

小型原计数/配置/轻量日志上GitHub，大型预测/权重留服务器并索引；共享记录不等于全部原件已上传。Test6历史暴露，禁读且不具独立final资格。发布前核对远端头，非强制快进，发布后回读；旧交接归档。
