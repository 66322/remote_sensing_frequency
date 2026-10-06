# 共享入口：N5已验收，交叉问题诊断包就绪

最新服务器登记回报（用户终端）：2026-10-06，新诊断目录research_post_n5_cross_20261006T235526_442218，控制器PID442590，NEW_TRAINING=0、E4_TILE_UNITS=192、GPU=0,1。目录时间标记23:55:26，nohup文件名时间23:55:38.454869；它们不是queue observed_at，尚未收到状态/存活/CPU阶段或GPU进度回报。原N5最后queue观测21:16:59已完成，未重启。

## 2026-10-06 诊断已登记，实际阶段待只读查询

日志位于/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_n5_cross_20261006T235526_442218/nohup_20261006T235538454869.log。登记回报只能确认安装器返回PID；按冻结启动链可推断启动前CPU检查成功返回，但未单收服务器cpu_checks.log，不能当CPU分析完成或GPU推理开始。若显卡空闲，可能尚在E3/边界CPU阶段，需status/preparation日志验证。

下一步仅运行该目录code/scripts/status_post_n5_cross.py并读取nohup/preparation日志；不要再次enqueue，不修改原N5/N2。R1/N3/S1训练未派发，诊断结束后接收原件再按已授权条件接续。登记原始摘录见records/research_post_n5_cross_20261006T235526_442218/user_reported_registration_20261006.json。


按[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)→[索引](experiments/rebuild_v1/INDEX.md)读取；GitHub 66322/remote_sensing_frequency、rebuild-v1-protocol-20260915为共享权威。

固定N5-3 gate=False、bilateral_candidate=False：T对随机N5-1仅+0.041878pp（要求≥0.5），clean/DSM全缺失对N5-0 −0.191071/−0.152271pp（底线−0.1）。RGB T在3_11负、5_10正。沿原冻结门槛关闭本次混合缺失配方的增量承诺，不换N5-2救gate、不扫比例/强度/预算/seed。普通适应仍是强控制，位置问题不整体关闭。

独立审计PASS：871载荷清单路径/大小匹配（连manifest872文件）；50载荷及manifest独立回读，124464次矩阵/原始指标与12304次joint校验，560个嵌入case重建匹配原源SHA，5040个预测索引绑定，固定gate/选模/监督与规则配额复算一致。未读取全部871载荷或服务器权重/影像/预测/mask本体；12项固定发布源码SHA匹配，44 mask元数据绑定匹配。

[完整N5报告](experiments/POST_N5_RESULTS_20261006.md)、[审计原件与复算](../records/post_n5_offline_audit_20261006/README.md)。普通N5-0 S=86.687264，随机/内容/混合86.365394/86.484846/86.392995；对旧模型不同年龄/共同裁剪的提升不能归给新内容机制。

下一步按[24—48小时交叉问题规划](protocols/POST_N5_CROSS_QUESTION_48H_PLAN_20261006.md)：先E3/N5后边界与E4-v2输入清零×特征删除×输出回退诊断，0训练。R1四组、N3五组、新S1四组构成13候选，但本窗口最多两个族8—9组，门槛通过才启动；默认R1+N3含诊断与交接目标27—44小时，实现时间另计。新交叉问题是建议，不改旧门槛/主线承诺。N4/R2不激活，诊断执行包已实现、CPU17项通过，已收服务器登记，实际阶段/存活待查询；R1/N3/S1训练包未实现，原N5/N2/诊断不重启。

研究阶段可行性探索；主线RGB–DSM双向条件互补与退化/缺失分割，恢复旁支。Potsdam fit12/Val2=3_11、5_10、native512/stride256、NoBoundary fg5主、Full诊断、seed42开发证据。仅GPU0/1、nohup、zzx对应目录；用户终端无SSH，无重复资源审计/Test6/independent final/held4读取、追加seed或失败配方重跑。N5失败不否定整个问题；N2/C/N1/A/B旧失败去留保持。


[冻结诊断执行协议](protocols/POST_N5_CROSS_DIAGNOSTICS_EXECUTION_20261006.md)、[本地就绪记录](../records/research_post_n5_cross_design_20261006/validation.json)：E3/边界→E4-v2三模型192推理单元、0训练。登记入口enqueue_post_n5_cross.py，完成后上传轻量原件，再按已有授权接续符合门槛的训练族；已获得实际目录/PID，但尚无存活/阶段观测，不声称GPU已运行。
