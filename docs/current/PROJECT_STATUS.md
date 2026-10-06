# 状态：N5四组完成，原件已独立验收

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


| 阶段 | 技术/科学状态 | 下一步 |
|---|---|---|
| N5四组 | 全COMPLETE/8000，selected全8000；固定N5-3 gate=False | 保存结果，不重训/换候选救gate |
| N5原件 | 1bd58b6，871载荷+manifest，独立复算PASS | [完整报告](../experiments/POST_N5_RESULTS_20261006.md) |
| N2/诊断 | 已完成验收；N2原gate失败、E1/E0问题筛选成立 | 不重启旧队列 |
| E3/N5边界复查 | 诊断三模型技术完成，原件待验收 | 决定区域族是否仍值得做 |
| N3 | 未实现/登记新运行 | 边界复查达到原门槛后匹配五组 |
| E4-v2/R1/S1 | E4-v2技术完成，N3/S1训练包未实现 | 三处处理分解，结果后取最多两族 |
| N4/R2 | N4无实际更新暴露；R2前提N5失败 | 保持不激活 |

固定N5-3 gate=False、bilateral_candidate=False：T对随机N5-1仅+0.041878pp（要求≥0.5），clean/DSM全缺失对N5-0 −0.191071/−0.152271pp（底线−0.1）。RGB T在3_11负、5_10正。沿原冻结门槛关闭本次混合缺失配方的增量承诺，不换N5-2救gate、不扫比例/强度/预算/seed。普通适应仍是强控制，位置问题不整体关闭。

独立审计PASS：871载荷清单路径/大小匹配（连manifest872文件）；50载荷及manifest独立回读，124464次矩阵/原始指标与12304次joint校验，560个嵌入case重建匹配原源SHA，5040个预测索引绑定，固定gate/选模/监督与规则配额复算一致。未读取全部871载荷或服务器权重/影像/预测/mask本体；12项固定发布源码SHA匹配，44 mask元数据绑定匹配。

N5从登记到queue完成约9h28m；GPU两波约9h25m，第一波约4h51m、第二波约4h34m。没有故障/自动重训回报。原plan继承旧族文字漂移在报告说明，不改科学原件；实际普通selected32/fixed22、内容各tag8条件。

研究阶段可行性探索，主线RGB–DSM双向条件互补与退化/缺失分割；恢复旁支。Potsdam fit12/Val2两tile、native512/stride256、NoBoundary fg5主，seed42开发证据，不称独立泛化。GPU0/1、nohup、zzx独立目录；用户终端无SSH，无Test6/independent final/held4读取/新seed/重复资源审计。其他历史审计范围不因本轮扩大，D30原矩阵缺口仍保留。
