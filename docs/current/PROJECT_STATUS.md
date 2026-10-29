# 当前状态：A0的DINOv2盘点、加载与测速已完成（2026-10-29）

- 科学历史：M2完成108训练/3,456,000更新/77,868评价；DF主判定未过，关闭该配方扩展。[报告](../experiments/PHASE3_M2_ACCEPTANCE_AND_CLOSEOUT_20261029.md)。
- 新研究交付：[规划](../experiments/POST_M2_CAPABILITY_PRIOR_PLAN_20261029.md)、[证据/文献审查](../experiments/POST_M2_EVIDENCE_AND_LITERATURE_AUDIT_20261029.md)、[准备表](../protocols/POST_M2_CAPABILITY_PREFLIGHT_20261029.md)、[机器计划](../../records/post_m2_capability_plan_20261029/plan.json)。总体路线仍为条件规划；[A0脚本](../../scripts/post_m2_a0.py)与[执行合同](../experiments/POST_M2_A0_EXECUTION_20261029.md)本地准备并通过4项检查，服务器已完成数据盘点与DINOv2真实加载，正式训练未启动；用户选定原remote_sensing环境就地升级；最新服务器输出显示conda已将Python3.9.21升级到3.11.13，用户随后使用中科大镜像完成Torch2.7.1+cu126、Torchvision0.22.1、Torchaudio2.7.1就地安装；pip check报告No broken requirements found，Torch实测CUDA12.6且cuda.is_available()=True。A0 inventory于20:07:39通过：F0所需12块数据齐全，DINOv2权重存在，192有效CPU核、约2.04TB可用内存，GPU0/1各空闲81081MiB；DINOv2 smoke于20:07:43通过，512输入产生1×384×37×37特征。首次profile因推理张量反传失败，修复后于20:18:55完成DINOv2 profile：160额外丢弃更新，选4 worker/micro16，候选中位数据等待+计算0.01093秒/步；评价batch16，529窗口整tile 0.4066秒；总profile 40.0秒，其中数据加载34.1秒。完整测速数值见[原样记录](../../records/post_m2_a0_capability_20261029/profile_dino2.json)。
- 新实验正式训练数=0；DINOv2真实加载/前向/测速完成；DINOv3源码/权重未配置，尚未真实加载；队列修改=0，DINOv2吞吐已实测，DINOv3吞吐与科学结果未知。默认单seed42小批次，阳性才加机制控制/地理折，必要时配对seed17；没有第三seed计划。
- 主线未自动切换。优先候选为新增能力及DSM几何关系；蒸馏/频率/优化条件进入，地图维护为独立候选。未宣称创新已成立或已达物理上限。
- 实际存储：第一次清理删除90权重、最后实际保留18，目录分配减少8.018GB；全盘free增量未确认。
- 后续清理：[工具](../experiments/PHASE3_M2_FINAL_COMPACTION_20261029.md)于19:15在服务器启动，离线统计读取到75,000/77,868 case后因mask-family指标空值相减而停止，未进入删除阶段；无新的分析/清理成功回执，最近实测保留18权重。用户要求暂缓清理，先升级原环境并启动A0；以后恢复清理须修复并核对失败回执。
- J仍为工程停止，无科学结果；用户本轮实测8张H100、GPU0/1各空闲81081 MiB；盘点显示192有效CPU核、约2.04TB可用内存。
- GitHub为跨电脑权威，历史与规划均可从当前入口接续；不重复哈希、不要求搬回某台电脑、不把工具/计划发布写成执行完成。
