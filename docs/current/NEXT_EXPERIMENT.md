# 下一步：复用已有预测诊断构成与边界，再决定N3

最后服务器回报：N5 queue观测2026-10-06T21:16:59.632381+08:00，N5_COMPLETE_AWAITING_REVIEW，四组COMPLETE/8000且selected全8000；用户status查询controller/worker LIVE=False（查询时刻未单列）。2026-10-06原件1bd58b6已收到，本次只做GitHub回读/离线复算，未新训练或GPU推理。

固定N5-3 gate=False、bilateral_candidate=False：T对随机N5-1仅+0.041878pp（要求≥0.5），clean/DSM全缺失对N5-0 −0.191071/−0.152271pp（底线−0.1）。RGB T在3_11负、5_10正。沿原冻结门槛关闭本次混合缺失配方的增量承诺，不换N5-2救gate、不扫比例/强度/预算/seed。普通适应仍是强控制，位置问题不整体关闭。

N5轻量原件已上传并独立验收，无需再次上传同一批、重训或重新登记。[报告](../experiments/POST_N5_RESULTS_20261006.md)、[原件](../../records/research_post_n5_20261006T114819_71934/evidence_20261006T222506485434_398074)。

1. 落实E3：A0/B1及必要N5扩展的同面积缺失类别×边界构成诊断；标签仅事后评价，不能从全局CM伪造分层。原问题gate保持，不把标准化描述当纯因果。
2. 用N5-0/N5-3的现有clean预测，按原E0 Full/4px边界、锚点正确并集harm/支持分母条件复查。两模型两个tile仍达门槛才准备N3五组。当前尚无这个后继回报/执行包，不能说N3已启动。
3. N3匹配局部/网格/RGB区域/DSM区域/双侧区域，从固定N1-2完整state、新8000/batch16/seed42重新开始，不叠失败N5。区域问题证据不等于方法有效。
4. E4可独立拆分清零与回退；R1只在新门槛通过后。N4等真实参数更新暴露；R2因N5不成立不激活。E5作边界诊断，不挽救原门槛。

既有按[扩展规划](../protocols/POST_N2_EXPANDED_PORTFOLIO_20261006.md)条件执行授权保持。后继须实现完整独立协议/代码、CPU与真实派发路径检查后再给服务器固定提交指令。不要重复运行已完成N5/N2/诊断。

研究阶段可行性探索，主线双向条件互补与退化/缺失分割，恢复旁支。Potsdam fit12/Val2两tile、native512/stride256、NoBoundary fg5主/Full诊断，仅GPU0/1、nohup、zzx对应目录；用户终端无SSH、无Test6/independent final/held4读取、追加seed/失败重跑/重复资源审计。
