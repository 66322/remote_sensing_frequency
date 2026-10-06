# 状态：N5四组完成，原件已独立验收

最后服务器回报：N5 queue观测2026-10-06T21:16:59.632381+08:00，N5_COMPLETE_AWAITING_REVIEW，四组COMPLETE/8000且selected全8000；用户status查询controller/worker LIVE=False（查询时刻未单列）。2026-10-06原件1bd58b6已收到，本次只做GitHub回读/离线复算，未新训练或GPU推理。

| 阶段 | 技术/科学状态 | 下一步 |
|---|---|---|
| N5四组 | 全COMPLETE/8000，selected全8000；固定N5-3 gate=False | 保存结果，不重训/换候选救gate |
| N5原件 | 1bd58b6，871载荷+manifest，独立复算PASS | [完整报告](../experiments/POST_N5_RESULTS_20261006.md) |
| N2/诊断 | 已完成验收；N2原gate失败、E1/E0问题筛选成立 | 不重启旧队列 |
| E3/N5边界复查 | 尚未执行，原预测可复用 | 决定区域族是否仍值得做 |
| N3 | 未实现/登记新运行 | 边界复查达到原门槛后匹配五组 |
| E4/R1 | E4新问题尚待诊断，R1未激活 | 清零/回退分解，不直接加置信网 |
| N4/R2 | N4无实际更新暴露；R2前提N5失败 | 保持不激活 |

固定N5-3 gate=False、bilateral_candidate=False：T对随机N5-1仅+0.041878pp（要求≥0.5），clean/DSM全缺失对N5-0 −0.191071/−0.152271pp（底线−0.1）。RGB T在3_11负、5_10正。沿原冻结门槛关闭本次混合缺失配方的增量承诺，不换N5-2救gate、不扫比例/强度/预算/seed。普通适应仍是强控制，位置问题不整体关闭。

独立审计PASS：871载荷清单路径/大小匹配（连manifest872文件）；50载荷及manifest独立回读，124464次矩阵/原始指标与12304次joint校验，560个嵌入case重建匹配原源SHA，5040个预测索引绑定，固定gate/选模/监督与规则配额复算一致。未读取全部871载荷或服务器权重/影像/预测/mask本体；12项固定发布源码SHA匹配，44 mask元数据绑定匹配。

N5从登记到queue完成约9h28m；GPU两波约9h25m，第一波约4h51m、第二波约4h34m。没有故障/自动重训回报。原plan继承旧族文字漂移在报告说明，不改科学原件；实际普通selected32/fixed22、内容各tag8条件。

研究阶段可行性探索，主线RGB–DSM双向条件互补与退化/缺失分割；恢复旁支。Potsdam fit12/Val2两tile、native512/stride256、NoBoundary fg5主，seed42开发证据，不称独立泛化。GPU0/1、nohup、zzx独立目录；用户终端无SSH，无Test6/independent final/held4读取/新seed/重复资源审计。其他历史审计范围不因本轮扩大，D30原矩阵缺口仍保留。
