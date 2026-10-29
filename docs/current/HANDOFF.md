# 当前交接：多路线规划v2，保留A0既有执行证据（2026-10-30）

先读[研究决定](RESEARCH_DECISION.md)、[多路线计划](../experiments/POST_M2_MULTIROUTE_PLAN_20261030.md)、[文献矩阵](../experiments/POST_M2_MULTIROUTE_LITERATURE_20261030.md)、[准备表](../protocols/POST_M2_MULTIROUTE_PREFLIGHT_20261030.md)、[状态](PROJECT_STATUS.md)、[下一步](NEXT_EXPERIMENT.md)。权威分支rebuild-v1-protocol-20260915；前版完整运行细节见[归档](../history/HANDOFF_BEFORE_MULTIROUTE_20261030.md)。

## 阶段、决定与角色

用户2026-10-30要求A0/A1/A2之外多视角规划，结合2025/2026研究并利用两张H100；本次已完成规划、来源核对和成本表。没有更换主线决定。S结构读出、G几何、Q质量训练成为独立首轮候选，基于现有DINOv2即可准备，不受A0科学阳性约束；A扩展为骨干×读出诊断，C/P有各自条件，E/F分别保留。

具体路线与预算为助手建议，不是已验证贡献。建议首轮15作业/96k（含原A0 4k）；新底座Full监督与A0 NB/128监督区分。新G/Q/S/C/P代码、包、真实吞吐、控制器和训练未完成。未采纳：静态融合信息论上限、PCGrad零误伤、EDL自动可靠、LoRA无遗忘、所有模块直接叠加、资源富余就三seed。

## 已核对的边界

A0真实512编码，DINOv2补至518；冻结bfloat16骨干、384→6浅头，训练128标签。新结构/联合训练不能沿用其速度估时。近期MM-DINO已直接做DINOv3遥感多模态，LiDeRe/AnyUp强读出、GKD分阶段蒸馏必须纳入对照视野。原D26/N2/C/M2的具体失败不扩张成整个问题失败；Full边界与NoBoundary不混比。

## 最后服务器回执与既有执行

最后观测2026-10-29 20:18:55：DINOv2修复no_grad后profile完成；160额外丢弃更新，4 worker/micro16约0.01093秒/步，整tile529窗口0.4066秒，总40秒含加载34.1秒。完整记录见[profile](../../records/post_m2_a0_capability_20261029/profile_dino2.json)。先前20:07:39 inventory确认F0 12tile、GPU0/1各81081MiB空闲、CPU192、可用RAM约2.04TB；不是实时状态。DINOv2 smoke真实前向通过。

原环境remote_sensing已升级Python3.11.13/Torch2.7.1+cu126/torchvision0.22.1/torchaudio2.7.1，pip check通过。A0执行绑定c22a046407daf42064cbb161429f2648c9b86d66；不因文档更新重做已通过检查或改快照。

DINOv3：本会话提供固定ModelScope ciqiangxu/DINOv3原生vits16 .pth下载方式；尚未收到DOWNLOAD_READY、真实加载或profile回执，不写已完成。只影响A分支。原A0授权保留，两模型合格后按既定配对合同接续；已收到正式训练回执数仍0。

本次没有连接服务器、下载权重、训练、评价、清理或修改队列。更新GitHub文档不等于部署新控制器。

## 历史与清理

M2于2026-10-29 08:43完成108训练/3,456,000更新/77,868评价，DF配方关闭；J 08:47:55因确定性CUDA CE失败停止，无科学结果。首清理11:05:39删除90保留18，目录分配减少8.018GB，未确认全盘free增量。

M2最终清理19:15在75,000/77,868读取后mask-family空值相减报错，未进删除；用户要求暂缓。最终退役授权不撤回，不为新计划强留18专家，也不假设其免费可用。恢复时先修首败，禁止直接重跑原--apply。新基线成本独立登记。

ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro。M2目录research_phase3_m2_revision_20261024T092814_2738345，combined目录research_phase3_combined_revision_20261024T092814_2738345。完整清理约定与失败边界见前版归档及[工具说明](../experiments/PHASE3_M2_FINAL_COMPACTION_20261029.md)。

下一步先具体化共同底座与S/G/Q最小对照、真实预算和执行载荷；A补缺失准备可并行。所有新结果保存逐tile int64 6×6矩阵、逐类/ROI/边界原始计数和配置/端点绑定，小记录同步GitHub回读。默认seed42，条件补配对17；不打开Val2/Test6/held4/final。
