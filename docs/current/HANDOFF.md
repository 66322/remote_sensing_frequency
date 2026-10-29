# 当前交接：A0首批代码与资源合同已准备，M2最终清理仍待回执（2026-10-29）

先读[研究决定](RESEARCH_DECISION.md)、[A0执行合同](../experiments/POST_M2_A0_EXECUTION_20261029.md)、[新计划](../experiments/POST_M2_CAPABILITY_PRIOR_PLAN_20261029.md)、[证据与文献核对](../experiments/POST_M2_EVIDENCE_AND_LITERATURE_AUDIT_20261029.md)、[准备表](../protocols/POST_M2_CAPABILITY_PREFLIGHT_20261029.md)。GitHub权威分支rebuild-v1-protocol-20260915供两台电脑接续，不以本机缓存替代最新远端。

## 本轮交付与下一项工作

A0首批的[scripts/post_m2_a0.py](../../scripts/post_m2_a0.py)、[本地合同测试](../../tests/test_post_m2_a0_contract.py)和[双H100执行合同](../experiments/POST_M2_A0_EXECUTION_20261029.md)已准备。本地3项纯合同测试通过；尚未在服务器验证DINOv3许可权重、新环境、真实模型加载或吞吐，也没有新训练/评价结果。旧M2环境Python3.9/Torch2.2.2不能直接视为A0可用。

服务器依次执行：inventory、双模型smoke、profile、各2000步训练、2块训练内校准、screen；只有通过才评价F0外层4块开发tile。两个H100物理卡各≥40GiB空闲且无计算进程；cgroup有效CPU≥12核和可用内存≥12GiB才并行，否则顺序。profile独立计入最多320额外丢弃优化更新，并测完整tile评价分段耗时；正式单seed42共4000优化更新、最多12次正式全tile评价。训练或评价超过预检2.5倍停队。子任务首败终止对方，不自动重试。

A0只是同视野浅层读出，尚未完成上下文/关系探针。A1四臂和阳性后的A2两控制沿[总体研究计划](../experiments/POST_M2_CAPABILITY_PRIOR_PLAN_20261029.md)条件推进，未实现、未排队。F0为开发折，不是独立最终验证。新A0不依赖旧M2训练端点，也不撤销最终大件清理授权。服务器结果上传GitHub后回读关键记录并更新本交接、状态与注册表。

## 服务器最后实际状态

- M2于2026-10-29 08:43完成108训练、77,868评价；G0/H2/G3通过，G1/G2/G4未过，DF配方关闭。[科学报告](../experiments/PHASE3_M2_ACCEPTANCE_AND_CLOSEOUT_20261029.md)。
- J于08:47:55因严格确定性下CUDA交叉熵不兼容停止，无科学结果，未重启。
- 第一次清理于11:05:39完成，删除90端点、保留18 R/D0；四目录分配量10.972GB→2.954GB，减少8.018GB，扣导出估计净减7.985GB；全盘free增量未确认。[回执](../experiments/PHASE3_M2_STORAGE_CLEANUP_RESULT_20261029.md)。
- GPU最后实际观测仍为10:29空闲，本轮没有服务器新观测。

## 未完成的收尾与retention

用户随后授权只留代码/配置/小结果等，退役剩余权重/推理/大统计；新策略替代“永久保留18”。[离线补充分析和最终清理工具](../experiments/PHASE3_M2_FINAL_COMPACTION_20261029.md)已实现/本地12项检查通过，尚无服务器执行回执。

原环境执行scripts/compact_phase3_m2.py --apply后，回传GITHUB_RELAY_SUMMARY或analysis_summary.json/cleanup_result.json，更新GitHub即可；不要求固定电脑下载大包。不训练、不推理、不用GPU、不修J、不重新哈希。先保存alpha/实际融合流量/逐类ROI/边界/校准/margin/掩码/轨迹摘要，再删大件。未知大文件核用途；共享数据/公共预训练不动。

ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro；M2目录research_phase3_m2_revision_20261024T092814_2738345；combined目录research_phase3_combined_revision_20261024T092814_2738345。清理输出records/m2_final_compaction_<时间>_<PID>/，单次回执records/phase3_m2_final_compaction_20261029.json；成功再次执行只报告ALREADY_COMPACTED，失败不自动重试。

没有回执不写剩余0/新分析完成/新增释放量。新计划不撤销清理，也不默认旧18专家可用；需要新基线时只重建最少匹配模型，成本明确。原108端点验收与事后删除分开。科学补充不翻转原alpha=.1/32k主门槛，不扩B/C，不开放封存split。
