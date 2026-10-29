# 当前状态：多路线规划v2已形成，服务器状态未更新（2026-10-30）

- 本次规划：[六路线](../experiments/POST_M2_MULTIROUTE_PLAN_20261030.md)、[近期文献](../experiments/POST_M2_MULTIROUTE_LITERATURE_20261030.md)、[准备表](../protocols/POST_M2_MULTIROUTE_PREFLIGHT_20261030.md)、[机器清单](../../records/post_m2_multiroute_plan_20261030/plan.json)。首轮建议A/G/Q/S与共享底座15作业96k；C/P条件批、E/F独立。不是已排队或已实现。
- 本次操作：只读论文/代码/小记录并更新规划；服务器连接、模型下载、正式训练、评价、清理、队列修改均为0。原A0脚本未改。
- **最后服务器观测2026-10-29 20:18:55**：DINOv2 profile通过，160额外丢弃更新；4 worker/micro16中位等待+计算0.01093秒/步，评价batch16、529窗口0.4066秒；总40秒、加载34.1秒。[完整原件](../../records/post_m2_a0_capability_20261029/profile_dino2.json)。该评价时间不含完整加载/CPU统计；不能外推新路线。
- 前序20:07:39 inventory通过：F0 12块齐全，CPU192有效核、约2.04TB可用RAM；GPU0/1各81081MiB空闲，其他卡占用，不扩大GPU范围。20:07:43 DINOv2真实512输入得到384×37×37特征。
- 原remote_sensing就地升级已完成：Python3.11.13、Torch2.7.1+cu126、torchvision0.22.1、torchaudio2.7.1、pip check通过；不默认重建。
- A0正式训练最新已收回执数=0；DINOv3下载/真实加载完成回执=0。本会话给出固定魔搭原生pth下载办法，但不能视为服务器已下载或来源/许可手续全部完成。A0执行代码固定c22a046407daf42064cbb161429f2648c9b86d66。
- M2于2026-10-29 08:43完成108训练、3,456,000更新、77,868评价；G0/H2/G3过，G1/G2/G4未过，DF配方关闭。[验收](../experiments/PHASE3_M2_ACCEPTANCE_AND_CLOSEOUT_20261029.md)。
- J于08:47:55工程停止，无科学结果。第一次清理11:05:39删除90/保留18，目录分配减少8.018GB，全盘free增量未确认。
- M2最终清理19:15在75,000/77,868 case后空值相减报错，未删除；用户暂缓，成功回执仍无。最后确认18，不写0。后续须修复首败，不能直接重复--apply。
- 科学主线未切换；所有新候选为待验证建议。F0反复使用只作开发；Val2/Test6/held4/final门禁不变。GitHub是跨电脑权威。
