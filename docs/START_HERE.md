# 共享入口：N5已验收，交叉问题诊断包就绪

最后服务器回报：N5 queue观测2026-10-06T21:16:59.632381+08:00，N5_COMPLETE_AWAITING_REVIEW，四组COMPLETE/8000且selected全8000；用户status查询controller/worker LIVE=False（查询时刻未单列）。2026-10-06原件1bd58b6已收到，本次只做GitHub回读/离线复算，未新训练或GPU推理。

按[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)→[索引](experiments/rebuild_v1/INDEX.md)读取；GitHub 66322/remote_sensing_frequency、rebuild-v1-protocol-20260915为共享权威。

固定N5-3 gate=False、bilateral_candidate=False：T对随机N5-1仅+0.041878pp（要求≥0.5），clean/DSM全缺失对N5-0 −0.191071/−0.152271pp（底线−0.1）。RGB T在3_11负、5_10正。沿原冻结门槛关闭本次混合缺失配方的增量承诺，不换N5-2救gate、不扫比例/强度/预算/seed。普通适应仍是强控制，位置问题不整体关闭。

独立审计PASS：871载荷清单路径/大小匹配（连manifest872文件）；50载荷及manifest独立回读，124464次矩阵/原始指标与12304次joint校验，560个嵌入case重建匹配原源SHA，5040个预测索引绑定，固定gate/选模/监督与规则配额复算一致。未读取全部871载荷或服务器权重/影像/预测/mask本体；12项固定发布源码SHA匹配，44 mask元数据绑定匹配。

[完整N5报告](experiments/POST_N5_RESULTS_20261006.md)、[审计原件与复算](../records/post_n5_offline_audit_20261006/README.md)。普通N5-0 S=86.687264，随机/内容/混合86.365394/86.484846/86.392995；对旧模型不同年龄/共同裁剪的提升不能归给新内容机制。

下一步按[24—48小时交叉问题规划](protocols/POST_N5_CROSS_QUESTION_48H_PLAN_20261006.md)：先E3/N5后边界与E4-v2输入清零×特征删除×输出回退诊断，0训练。R1四组、N3五组、新S1四组构成13候选，但本窗口最多两个族8—9组，门槛通过才启动；默认R1+N3含诊断与交接目标27—44小时，实现时间另计。新交叉问题是建议，不改旧门槛/主线承诺。N4/R2不激活，诊断执行包已实现、CPU17项通过，尚无服务器登记回报；R1/N3/S1训练包未实现，原N5/N2/诊断不重启。

研究阶段可行性探索；主线RGB–DSM双向条件互补与退化/缺失分割，恢复旁支。Potsdam fit12/Val2=3_11、5_10、native512/stride256、NoBoundary fg5主、Full诊断、seed42开发证据。仅GPU0/1、nohup、zzx对应目录；用户终端无SSH，无重复资源审计/Test6/independent final/held4读取、追加seed或失败配方重跑。N5失败不否定整个问题；N2/C/N1/A/B旧失败去留保持。


[冻结诊断执行协议](protocols/POST_N5_CROSS_DIAGNOSTICS_EXECUTION_20261006.md)、[本地就绪记录](../records/research_post_n5_cross_design_20261006/validation.json)：E3/边界→E4-v2三模型192推理单元、0训练。登记入口enqueue_post_n5_cross.py，完成后上传轻量原件，再按已有授权接续符合门槛的训练族；未获得实际目录/PID前不声称运行。
