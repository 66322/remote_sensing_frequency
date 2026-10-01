# Start Here

共享记录权威入口：66322/remote_sensing_frequency，分支`rebuild-v1-protocol-20260915`。实验快照基准`1a8a840`，D23执行入口`40fca5a`。用户两台电脑轮流工作，**以本远端分支为准，本地仅工作副本**。见[记录与交接规则](protocols/RECORD_SOURCE_AND_HANDOFF.md)。

1. [研究定位与去留决策](current/RESEARCH_DECISION.md)：论文可行性探索，频率＋语义可靠性优先候选，C1旁支，允许换解法/问题/方向；最终章节未冻结。
2. [当前交接](current/HANDOFF.md)与[当前状态](current/PROJECT_STATUS.md)：最新观测、证据边界与决定。
3. [下一步](current/NEXT_EXPERIMENT.md)：D23-A已通过准备门槛；B代码已实现、工程尾部已回传，当前上传完整绑定和原摘要到GitHub，由助手回读，不重跑已有诊断，不默认启动正式训练。
4. [不可重复事项](current/DO_NOT_REPEAT.md)、[实验索引](experiments/rebuild_v1/INDEX.md)与[机器台账](../records/rebuild_v1_experiment_registry.json)。
5. [D23原方案](protocols/D23_DENSE_BENEFIT_FEASIBILITY_20261001.md)、[B执行说明](protocols/D23_B_ENGINE_ADMISSION_20261001.md)、[工程尾部核对](experiments/D23_B_ENGINE_TAIL_AUDIT_20261001.md)。代码已实现、工程可运行、已知缺失回退、精度保护及独立泛化分别报告。

服务器大型预测/权重/日志仍在/home/jovyan/zzx，GitHub仅保存已接收的小型原计数/摘要/配置/索引。最新片段补齐GPU1完成时钟与CPU报告；GPU0完整头部仍待原件。长输出按[轻量上传规则](protocols/LIGHT_RECORD_UPLOAD_20261001.md)直接上传本分支，用户仅回复提交号。紧凑记录不是全部原件。Test6已历史暴露，保持禁读，不具独立final资格。

切换电脑先读远端入口；每次重要工作将交接/状态/下一步和证据写回同一分支并回读，回复给提交和链接。发布前核对最新分支头，不强制覆盖另一台新提交。技术事实与文档冲突时核对原证据并修正GitHub。

此前Post-D21/D21结论及局部负结果保留，见[证据缺口](experiments/RESEARCH_GAPS_AND_DECISION_20261001.md)、[Post-D21结果](experiments/POST_D21_FINAL_AND_MIXED_FOLLOWUP_RESULTS_20261001.md)、[逐tile风险](experiments/POST_D21_MIXED_TILE_RISK_RESULTS_20261001.md)。近期工程成功不自动证明语义/频率贡献。
