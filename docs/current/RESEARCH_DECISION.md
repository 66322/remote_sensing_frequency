# 研究阶段与当前决定：N5固定配方停止，区域问题待复查

最后服务器回报：N5 queue观测2026-10-06T21:16:59.632381+08:00，N5_COMPLETE_AWAITING_REVIEW，四组COMPLETE/8000且selected全8000；用户status查询controller/worker LIVE=False（查询时刻未单列）。2026-10-06原件1bd58b6已收到，本次只做GitHub回读/离线复算，未新训练或GPU推理。

研究阶段仍可行性探索；主线RGB–DSM双向条件互补与退化/缺失分割；任务驱动恢复旁支。本次不改变论文章节或承诺新方法。

## 2026-10-06 N5去留与来源
固定N5-3 gate=False、bilateral_candidate=False：T对随机N5-1仅+0.041878pp（要求≥0.5），clean/DSM全缺失对N5-0 −0.191071/−0.152271pp（底线−0.1）。RGB T在3_11负、5_10正。沿原冻结门槛关闭本次混合缺失配方的增量承诺，不换N5-2救gate、不扫比例/强度/预算/seed。普通适应仍是强控制，位置问题不整体关闭。

决定来源为[事前执行协议](../protocols/POST_N5_EXECUTION_20261006.md)及[已验收结果](../experiments/POST_N5_RESULTS_20261006.md)，不是另改门槛。局部缺失改善主要可由随机控制解释，并伴随原条件精度代价；不能从该具体混合配方失败推断位置问题消失或双模态问题不成立。N5-2最高T不替代固定候选。

独立审计PASS：871载荷清单路径/大小匹配（连manifest872文件）；50载荷及manifest独立回读，124464次矩阵/原始指标与12304次joint校验，560个嵌入case重建匹配原源SHA，5040个预测索引绑定，固定gate/选模/监督与规则配额复算一致。未读取全部871载荷或服务器权重/影像/预测/mask本体；12项固定发布源码SHA匹配，44 mask元数据绑定匹配。

## 下一不确定性及条件顺序
沿[扩展规划](../protocols/POST_N2_EXPANDED_PORTFOLIO_20261006.md)先复用已有预测补E3构成与N5-0/N5-3的clean Full边界问题。只有两者仍满足原≥1pp/支持分母条件，才落实N3五组；每族固定N1-2完整基座、新8000匹配局部/网格/两单侧，不叠失败N5或选后验最高模型。边界提示不是区域方法成立。

E4拆解输入清零/输出回退是独立新问题；R1仅E4门槛通过，原E2 gate不改判。N4仍无实际参数更新暴露，像素/规则计数相同或非零梯度不足以触发。R2要求两父族各自成立，N5失败故本轮不激活。E5只作形状边界，不救gate。当前未登记新后继，既有按规划条件执行授权保持。

未采纳全跑21组、扫混合比例/强度/预算/seed、N5-2替主候选、T重复调配方、Test6/独立final、把像素/条件当重复做显著性。方向/tile、工程回退、开发保护与独立泛化分别报告。

## 既有决定保持
N2 3×3关系固定gate失败、A2/B3/C2/N1-3失败去留不变，F/N6跳过。详见[索引](../experiments/rebuild_v1/INDEX.md)及[此前验收](../experiments/POST_N2_E0_E1_E2_RESULTS_20261006.md)。不回写旧原件，不以本轮补齐全部历史数据。

仅GPU0/1、nohup、zzx对应目录；用户终端无SSH，Potsdam fit12/Val2=3_11、5_10，native512/stride256、NoBoundary fg5主，seed42开发证据。无Test6/independent final/held4读取、新seed或重复资源审计。[交接](HANDOFF.md)、[下一步](NEXT_EXPERIMENT.md)。
