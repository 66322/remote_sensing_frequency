# 研究阶段与决定

最后服务器观测（用户2026-10-06回传）：queue_status观测时间2026-10-05T23:27:15.831648+08:00，诊断后继DIAGNOSTICS_COMPLETE_AWAITING_REVIEW，PID3591245 LIVE=False；E0/MASKS COMPLETE，E1_A0/B1及E2_N1-2/N2-0/N2-3五项全部COMPLETE，worker均LIVE=False，新增optimizer更新0。nohup已记录READY N2_COMPLETE_AWAITING_STAGE_PROTOCOL和完整派发/完成序列，无本次故障回报。POST_N2_DIAGNOSTICS_SCREEN True True对应N5问题触发=True、N3问题触发=True，不是两种训练方法有效。N2原科学gate、诊断数值/原件尚待上传回读；不可称已独立验收或确认贡献。

研究阶段仍为可行性探索；主线RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复旁支。Potsdam fit12/Val2=3_11、5_10，native512/stride256、NoBoundary fg5为主、Full为诊断；单seed42开发证据。只用GPU0/1、nohup、全部产物留zzx对应目录；无SSH、无Test6/independent final、无追加种子、无失败配方自动追训，F/N6保持跳过。

## 2026-10-06：技术完成后先接收与分析，不直接增加训练

本轮N2已被后继读取为完成、诊断全部技术完成。N3/N5问题筛选报告均True；先复核原N2科学gate、E0分母/跨tile效果、E1规则/方向/类别构成和E2成本，再按原[规划](../protocols/POST_N2_EVIDENCE_LED_PLAN_20261005.md)只落实证据充分的一族。该顺序来自此前冻结协议和用户开始授权，不把简报中的True写成方法有效或方向变更。

未采纳直接启动全部13组、扩窗口/预算/种子救N2、重训A/B/C/N1、把E2漏报信号自动升级置信网络贡献。T仍预留到N5完整协议冻结后。当前没有新的科学去留结论；N2原件未接收，不能提前称其成功或失败。C正确掩码KL、N1-3多深度入口、A2/B3旧固定gate失败去留保持。

[下一步](NEXT_EXPERIMENT.md)上传原件；[交接](HANDOFF.md)列研究问题、来源、未采纳建议与不确定性。

## 历史科学决定（运行态以本页最新观测为准）

## 已采纳决定及来源

用户要求继续双模态研究，并授权Post-D30 A/B/C主体18组、B3过门槛后F4组；授权不等于机制已成立。执行协议见[Post-D30](../protocols/POST_D30_EXECUTION_20261003.md)。原D29未激活；D23—D30具体失败配方不追加追训/扫参/种子挽救。

当前换机制的理由是普通融合有效，而旧门控/路由/保护恢复没有增量；A检验对齐范围，B检验局部对应修正是否超过增强，C检验缺失知识迁移是否超过同位置硬标签加权。未决定转第2章、未承诺频率贡献、未选事后最佳敏感性组代替固定候选。相关文献与交叉假设见[原规划](../protocols/POST_D30_PORTFOLIO_20261003.md)及[研究机会](../experiments/ASSUMPTIONS_AND_RESEARCH_OPPORTUNITIES_20261003.md)。

## 去留与证据边界

A固定A2对A0/A1/A3；B固定B3对普通增强与打乱对照；C按原教师/硬标签对照判断；F仅固定B3全部gate通过。普通方法追平则保留解释性结论并关闭复杂机制。达到预设增量后才另立多seed/真正独立来源确认，不自动读取Test6。所有旧结论见[总台账](../experiments/rebuild_v1/INDEX.md)，不把技术完成等同科学成立。


## Post-D30 A/B去留更新（2026-10-04）

固定A2 gate=False：综合对A0+0.101643pp（要求≥+0.2）、对A1−0.044694pp（要求≥+0.2）、对A3−0.023958pp（要求≥+0.1）；其余原生安全/fixed检查通过。固定B3 gate=False：几何对B1+0.021260pp（要求≥+0.5）、对B4−0.012852pp（要求≥+0.2）；DSM锚点正确伤害率较A0增加0.011997pp。F触发条件不成立；不追加A/B种子、追训、扫参或换敏感性最佳组救gate。原C继续。

来源为原冻结门槛与已接收原件，不是研究主线变更；未采纳追加种子、预算或换敏感性组救gate。下一不确定性仍为C是否超过同位置硬标签/教师对照，按原双侧门槛去留。见[结果](../experiments/POST_D30_AB_RESULTS_20261004.md)。



本次控制器修复：None超时按原定8小时处理；验证PID/启动tick/任务参数、完成SHA及待派发目录。修复文件另存原N2实验的controller_repair_*，worker仍执行原86b6快照。CPU恢复11项（含实际监控循环）与原N2八项检查通过，七文件语法检查通过；这些不代表真实CUDA任务成功。详见[修复说明](../experiments/POST_AB_N2_CONTROLLER_REPAIR_20261005.md)。



