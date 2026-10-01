# Start Here

共享记录权威：66322/remote_sensing_frequency 的 `rebuild-v1-protocol-20260915` 分支；`1a8a840` 是历史实验基准，不是最新启动版本。两台电脑均从本入口进入，不能以本地旧交接覆盖远端。

**资源已明确：GPU0、GPU1，两张H100 80GB，主机内存和硬盘充足；长实验nohup，全部产物在 /home/jovyan/zzx 对应实验目录。新对话直接复用已完成验收，不从资源审计重新开始。**

按顺序读取：

1. [当前交接](current/HANDOFF.md)：最后观测、实验目的、执行绑定及证据边界。
2. [下一步](current/NEXT_EXPERIMENT.md)：接续现有工作，不能照历史命令重复停机/启动。
3. [长期执行约定](protocols/EXECUTION_CONTRACT.md)：资源、nohup、目录、禁止重复审计及吞吐优化边界。

研究规划时读[研究决策](current/RESEARCH_DECISION.md)，而不是从最近的正结果推断方向。当前问题是频率与语义可靠性对RGB–DSM退化/缺失融合是否有独立收益；仍在可行性探索，C1任务驱动恢复为旁支，部分解冻为强基线，允许换解法/问题/方向，章节贡献未冻结。

按任务需要查[状态](current/PROJECT_STATUS.md)、[不可重复事项](current/DO_NOT_REPEAT.md)、[机器台账](../records/rebuild_v1_experiment_registry.json)、[实验索引](experiments/rebuild_v1/INDEX.md)和[记录规则](protocols/RECORD_SOURCE_AND_HANDOFF.md)。只读核对已有证据不等于重跑审计。

小型原计数、配置和轻量日志上传GitHub；大型预测/权重/归档留服务器并索引。GitHub有记录不代表已接收全部原件。Test6历史暴露，禁读且不具独立final资格。发布前检查远端最新头，非强制快进，发布后回读；更新精简交接，旧交接归档。
