# 当前交接：优先准备并启动A0，M2最终清理暂停（2026-10-29）

先读[研究决定](RESEARCH_DECISION.md)、[A0执行合同](../experiments/POST_M2_A0_EXECUTION_20261029.md)、[新计划](../experiments/POST_M2_CAPABILITY_PRIOR_PLAN_20261029.md)、[证据与文献核对](../experiments/POST_M2_EVIDENCE_AND_LITERATURE_AUDIT_20261029.md)、[准备表](../protocols/POST_M2_CAPABILITY_PREFLIGHT_20261029.md)。GitHub权威分支rebuild-v1-protocol-20260915供两台电脑接续，不以本机缓存替代最新远端。

## 本轮交付与下一项工作

A0首批的[scripts/post_m2_a0.py](../../scripts/post_m2_a0.py)、[本地合同测试](../../tests/test_post_m2_a0_contract.py)和[双H100执行合同](../experiments/POST_M2_A0_EXECUTION_20261029.md)已准备。本地4项检查通过；服务器已验证数据与DINOv2真实模型加载，DINOv3许可权重/加载和两个模型吞吐仍未知，没有新训练/评价结果。服务器2026-10-29先实测Python3.9.21/Torch2.2.2+cu121、驱动590.48.01，GPU0/1各空闲81081 MiB；用户选择就地升级原remote_sensing环境、不新建环境，M2最终清理暂停。随后conda Python3.11.13事务成功，使用中科大镜像安装Torch2.7.1+cu126、Torchvision0.22.1、Torchaudio2.7.1；pip check为No broken requirements found，Torch实测CUDA12.6可用。A0 inventory于20:07:39通过，F0的12块数据齐全，192有效CPU核、约2.04TB可用内存，GPU0/1各81081MiB空闲；DINOv2 smoke于20:07:43通过，512输入输出384×37×37特征。DINOv2首次profile在第一步因冻结特征是推理张量、读出头无法反传而失败；已将冻结教师特征抽取改为no_grad，本地反传回归测试通过。下一关只重下新脚本并重跑DINOv2 profile，不重跑已写入的smoke；DINOv3源码/权重尚未配置。

服务器依次执行：inventory、双模型smoke、profile、各2000步训练、2块训练内校准、screen；只有通过才评价F0外层4块开发tile。两个H100物理卡各≥40GiB空闲且无计算进程；cgroup有效CPU≥12核和可用内存≥12GiB才并行，否则顺序。profile独立计入最多320额外丢弃优化更新，并测完整tile评价分段耗时；正式单seed42共4000优化更新、最多12次正式全tile评价。训练或评价超过预检2.5倍停队。子任务首败终止对方，不自动重试。

A0只是同视野浅层读出，尚未完成上下文/关系探针。A1四臂和阳性后的A2两控制沿[总体研究计划](../experiments/POST_M2_CAPABILITY_PRIOR_PLAN_20261029.md)条件推进，未实现、未排队。F0为开发折，不是独立最终验证。新A0不依赖旧M2训练端点，也不撤销最终大件清理授权。服务器结果上传GitHub后回读关键记录并更新本交接、状态与注册表。

## 服务器最后实际状态

- M2于2026-10-29 08:43完成108训练、77,868评价；G0/H2/G3通过，G1/G2/G4未过，DF配方关闭。[科学报告](../experiments/PHASE3_M2_ACCEPTANCE_AND_CLOSEOUT_20261029.md)。
- J于08:47:55因严格确定性下CUDA交叉熵不兼容停止，无科学结果，未重启。
- 第一次清理于11:05:39完成，删除90端点、保留18 R/D0；四目录分配量10.972GB→2.954GB，减少8.018GB，扣导出估计净减7.985GB；全盘free增量未确认。[回执](../experiments/PHASE3_M2_STORAGE_CLEANUP_RESULT_20261029.md)。
- 用户随后实测8张H100；A0 inventory确认GPU0/1各81081 MiB空闲、有效CPU 192核、可用内存约2.04TB，GPU2–7有既有计算进程，A0继续只用0/1。DINOv2 smoke通过，profile首次工程失败且无正式结果；修复待服务器复跑。2026-10-29 19:15启动M2最终清理，但在完成75,000/77,868 case读取后，mask-family指标空值相减触发TypeError；脚本在删除阶段前停止，尚无新的清理结果。用户要求暂停M2清理，先准备环境并启动A0。

## 未完成的收尾与retention

用户随后授权只留代码/配置/小结果等，退役剩余权重/推理/大统计；新策略替代“永久保留18”。[离线补充分析和最终清理工具](../experiments/PHASE3_M2_FINAL_COMPACTION_20261029.md)原版已实现/本地12项检查通过；服务器首轮在预删除统计阶段失败，失败日志见用户2026-10-29粘贴输出，尚无成功回执。按用户新顺序暂缓，不作为A0门槛。

后续恢复M2清理时，须先针对已保存的失败回执验证并修复；不得直接重复执行原版--apply。成功后回传GITHUB_RELAY_SUMMARY或analysis_summary.json/cleanup_result.json，再更新GitHub；不要求固定电脑下载大包。不训练、不推理、不用GPU、不修J、不重新哈希。先保存alpha/实际融合流量/逐类ROI/边界/校准/margin/掩码/轨迹摘要，再删大件。未知大文件核用途；共享数据/公共预训练不动。

ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro；M2目录research_phase3_m2_revision_20261024T092814_2738345；combined目录research_phase3_combined_revision_20261024T092814_2738345。清理输出records/m2_final_compaction_<时间>_<PID>/，单次回执records/phase3_m2_final_compaction_20261029.json；成功再次执行只报告ALREADY_COMPACTED，失败不自动重试。

没有回执不写剩余0/新分析完成/新增释放量。新计划不撤销清理，也不默认旧18专家可用；需要新基线时只重建最少匹配模型，成本明确。原108端点验收与事后删除分开。科学补充不翻转原alpha=.1/32k主门槛，不扩B/C，不开放封存split。
