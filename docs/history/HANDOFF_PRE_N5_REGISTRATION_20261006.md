# 当前交接：N5四组执行包就绪，等待用户服务器登记回报

## 最后观测与工作
最后服务器观测：N2 2026-10-05T22:11:34.641183+08:00六组COMPLETE；诊断23:27:15.831648全部COMPLETE。原件已独立验收；本次没有新的服务器查询/登记或训练结果。

用户2026-10-06明确“按上述规划进行实验”。已落实第一批N5四组完整独立执行包：[协议](../protocols/POST_N5_EXECUTION_20261006.md)，CPU15项、语法11文件通过，[记录](../../records/post_n5_execution_design_20261006/validation.json)。覆盖actual controller派发/失败阻断/汇总调用与退出、null timeout、固定完整基座、whole-tile mask及裁剪/监督匹配、fixed gate和上传编码。局部测试环境Python3.13/Torch2.7.1+cpu；服务器登记再用原EXP_PY复查，真实CUDA首步待回报。每批8原槽、8新增槽；所有组新增槽共同native512/128格对齐，保证每个缺失样本25%，T不参与训练/选模。

## 研究阶段、决定与去留
可行性探索；主线RGB–DSM双向条件互补与退化/缺失分割，恢复旁支。N2固定gate失败，不救当前3×3实现；E1仅RGB/H问题触发，E0提示边界困难，E2说明硬回退不保证最优。沿原顺序N5先执行；21组是条件储备上限，增加数量不构成方法成立。N5各组固定N1-2完整state、新8000更新，同容量/训练预算；候选N5-3对随机N5-1，T与旧保护线冻结。不选N2后验最高，不删L或方向救gate。

N5完成后先接收分析，再落实E3/E5及N3边界筛选；E4/E6与R1/N4/R2按各自条件独立准备。它们尚未被本次入口派发；N5控制器完成后退出，不默认接续未实现占位项。未采纳直接全跑21组、N2追训/窗口/seed、T调参、Test6或伪重复显著性。

## 立即执行与故障处理
用户终端从本次固定提交提取scripts/enqueue_post_n5.py执行；不用checkout替换服务器源码。入口先查询原N1/N2/诊断queue、完成绑定、controller/worker及锁；已有N5则只报告，不重复登记。登记成功返回新目录、controller PID和nohup log。下一步用返回目录的status_post_n5.py和日志检查，不能无回报声称已运行。

只GPU0/1、每卡一worker、两波；nohup，所有快照/缓存/临时/记录在zzx新实验目录。用户执行终端，无SSH，不重复资源审计；无Test6/independent final/held4、新seed或失败配方重跑。超时12h/job、6h CPU，拒绝null；技术故障停止派发，已有worker可能继续，明确诊断/接管，不重复入口挽救。

Potsdam fit12/Val2=3_11、5_10，native512/stride256、NoBoundary fg5主、Full诊断。四组完成N5_COMPLETE_AWAITING_REVIEW后上传轻量原件，权重/预测/mask仅服务器索引；原N2/诊断无需重启。

[下一步](NEXT_EXPERIMENT.md)；[研究决定](RESEARCH_DECISION.md)；[扩展规划](../protocols/POST_N2_EXPANDED_PORTFOLIO_20261006.md)；[上一交接](../history/HANDOFF_PRE_N5_EXECUTION_20261006.md)。
