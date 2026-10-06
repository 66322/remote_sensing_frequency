# 研究阶段与当前决定：N5固定配方停止，区域问题待复查

最后服务器查询（用户终端）：QUERY_OBSERVED=2026-10-07T07:38:05.617099+08:00；queue最后更新2026-10-07T01:08:32.994625+08:00，CROSS_DIAGNOSTICS_COMPLETE_AWAITING_REVIEW。CPU完成，三个E4作业COMPLETE，查询时控制器及worker均LIVE=False，新增optimizer更新0。回报screen output=False、feature=True、boundary=True，NEXT_FAMILIES=['N3','S1']；原计数/绑定尚未上传验收。

## 2026-10-07 诊断完成回报：原件待上传

最后服务器查询（用户终端）：QUERY_OBSERVED=2026-10-07T07:38:05.617099+08:00；queue最后更新2026-10-07T01:08:32.994625+08:00，CROSS_DIAGNOSTICS_COMPLETE_AWAITING_REVIEW。CPU完成，三个E4作业COMPLETE，查询时控制器及worker均LIVE=False，新增optimizer更新0。回报screen output=False、feature=True、boundary=True，NEXT_FAMILIES=['N3','S1']；原计数/绑定尚未上传验收。

固定输出对比A1B1C0−A1B1C1：RGB N1-2 −0.299884pp、N2-0 +0.401156pp，两个模型均tile异号，原门槛False，R1本轮不启动。固定特征对比A1B0C0−A1B1C0是在C=0条件下：RGB N1-2 +1.307603pp、N2-0 +0.577591pp，均两tile正；N2-3预定旁证+0.595287pp。DSM对应收益约+0.002574/−0.026330/−0.033523pp，不支持双向方法收益。不能把“在保留融合输出时保留上下文特征”的条件增量写成单独删除mask必定有效。

候选接续N3五组+S1四组，沿原优先级与9组上限；不因R1未触发追加别族填时长。boundary=True目前只有控制器screen转录，N5-0/N5-3逐tile分母和构成统计尚未独立接收。先显式upload_post_n5_cross_records.py上传原轻量记录，核对CM/joint、所有路径binding和parity后再冻结训练包。既有用户执行授权保持，不再索取训练许可；当前训练代码未实现/派发。

N1-2/N2-0/N2-3完整worker耗时约34m56s/35m01s/35m16s。nohup文件时间标记23:55:38至queue完成01:08:33约72m55s，即约1h13m；文件名起点是粗墙钟参照，不改写为独立精确启动观测。此前2—4h估计保留为规划范围，当前完整诊断已结束，不再继续估剩余时间。原件转录见records/research_post_n5_cross_20261006T235526_442218/user_reported_complete_20261007T073805.json。


## 2026-10-06：诊断两卡E4推理已确认，等待完成原件

用户“按上述规划进行吧”已授权落实第一阶段。[冻结执行协议](../protocols/POST_N5_CROSS_DIAGNOSTICS_EXECUTION_20261006.md)：E3/原N5边界复查复用预测，E4-v2八路径×三固定模型×两状态×两方向×两tile=192推理单元，新增训练更新0。CPU17项及10文件语法通过；包含实际N1/N2前向配合合成专家的路径一致性/全缺失保护、两lane派发/失败/超时、完整192模拟case独立汇总退出。非真实DINO/checkpoint/GPU验证；登记前服务器同包再检查。

新入口enqueue_post_n5_cross.py幂等查询旧队列/本类登记，继承原N5快照并逐SHA核验，再nohup。新目录research_post_n5_cross_<timestamp>_<pid>；只GPU0/1，CPU6h/每模型8h有限超时，技术故障HOLD、不自动重试。预计诊断2—4h非实测。当前三模型技术完成，screen已转录；原始计数/绑定仍待上传独立验收。

完成态CROSS_DIAGNOSTICS_COMPLETE_AWAITING_REVIEW，原件接收/复算后按已授权条件继续至多两训练族。R1/N3/S1训练代码仍未实现，不伪造为可派发预约，也不是再次等待训练许可。旧N5/N2/诊断不重启；旧gate/主线不变。


## 2026-10-06：一到两天交叉问题规划更新（尚未执行）

用户要求更多实验，并允许评估换交叉问题。新[24—48小时规划](../protocols/POST_N5_CROSS_QUESTION_48H_PLAN_20261006.md)建议优先E4-v2输入清零×内部特征删除×输出回退三因素诊断，同时做E3/N5后边界复查；原E4的2×2扩为8路径，避免混淆内部掩码与输出策略。N1源码已核对，N2扩展路径须执行包继续确认。

候选训练R1四组、N3五组、新S1四组，共13组设计；本窗口至多两族8—9组，诊断通过才启动。默认R1+N3预计计算/诊断25—38h，含交接余量目标27—44h，执行包实现时间另计、非时限保证。S1作为上下文特征可用性替代问题，不把13组全跑。优先级变化来自N5/N2匹配增量失败与E2约1pp待归因现象；主线角色不变，新研究问题为建议，旧gate不改判。

当前诊断执行包已完成并已收screen转录；最后服务器观测仍为上文N5完成。既有条件执行授权保持。N4无更新暴露、R2因N5失败不激活，不重训失败族、不加seed/Test6。下一步上传已完成诊断轻量原件，再接收原件依结果选择研究族。


研究阶段仍可行性探索；主线RGB–DSM双向条件互补与退化/缺失分割；任务驱动恢复旁支。本次不改变论文章节或承诺新方法。

## 2026-10-06 N5去留与来源
固定N5-3 gate=False、bilateral_candidate=False：T对随机N5-1仅+0.041878pp（要求≥0.5），clean/DSM全缺失对N5-0 −0.191071/−0.152271pp（底线−0.1）。RGB T在3_11负、5_10正。沿原冻结门槛关闭本次混合缺失配方的增量承诺，不换N5-2救gate、不扫比例/强度/预算/seed。普通适应仍是强控制，位置问题不整体关闭。

决定来源为[事前执行协议](../protocols/POST_N5_EXECUTION_20261006.md)及[已验收结果](../experiments/POST_N5_RESULTS_20261006.md)，不是另改门槛。局部缺失改善主要可由随机控制解释，并伴随原条件精度代价；不能从该具体混合配方失败推断位置问题消失或双模态问题不成立。N5-2最高T不替代固定候选。

独立审计PASS：871载荷清单路径/大小匹配（连manifest872文件）；50载荷及manifest独立回读，124464次矩阵/原始指标与12304次joint校验，560个嵌入case重建匹配原源SHA，5040个预测索引绑定，固定gate/选模/监督与规则配额复算一致。未读取全部871载荷或服务器权重/影像/预测/mask本体；12项固定发布源码SHA匹配，44 mask元数据绑定匹配。

## 下一不确定性及条件顺序
此前顺序沿[扩展规划](../protocols/POST_N2_EXPANDED_PORTFOLIO_20261006.md)优先E3构成与N5-0/N5-3的clean Full边界问题；本次按上文新规划把E4-v2并列诊断、R1条件优先。只有两者仍满足原≥1pp/支持分母条件，才落实N3五组；每族固定N1-2完整基座、新8000匹配局部/网格/两单侧，不叠失败N5或选后验最高模型。边界提示不是区域方法成立。

E4拆解输入清零/输出回退是独立新问题；R1仅E4门槛通过，原E2 gate不改判。N4仍无实际参数更新暴露，像素/规则计数相同或非零梯度不足以触发。R2要求两父族各自成立，N5失败故本轮不激活。E5只作形状边界，不救gate。当前未登记新后继，既有按规划条件执行授权保持。

未采纳全跑21组、扫混合比例/强度/预算/seed、N5-2替主候选、T重复调配方、Test6/独立final、把像素/条件当重复做显著性。方向/tile、工程回退、开发保护与独立泛化分别报告。

## 既有决定保持
N2 3×3关系固定gate失败、A2/B3/C2/N1-3失败去留不变，F/N6跳过。详见[索引](../experiments/rebuild_v1/INDEX.md)及[此前验收](../experiments/POST_N2_E0_E1_E2_RESULTS_20261006.md)。不回写旧原件，不以本轮补齐全部历史数据。

仅GPU0/1、nohup、zzx对应目录；用户终端无SSH，Potsdam fit12/Val2=3_11、5_10，native512/stride256、NoBoundary fg5主，seed42开发证据。无Test6/independent final/held4读取、新seed或重复资源审计。[交接](HANDOFF.md)、[下一步](NEXT_EXPERIMENT.md)。
