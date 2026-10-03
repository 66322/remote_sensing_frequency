# 当前状态：D26科学复核完成，D27待接口修复补跑

2026-10-03更新。D26最后服务器观测04:04:45.239849+08:00 COMPLETE9/9，D27最后观测04:12:45.117489+08:00 COMPLETE_WITH_TECHNICAL_FAILURES，0/10。D27接力后十组step0同KeyError treatment，无评价/完成checkpoint。[完整复核](../experiments/D26_COMPLETE_D27_FAILURE_REVIEW_20261003.md)。

D26九组180份主条件tile6×6原整数矩阵独立重算，四族分数/选中SHA与汇总一致。XSF S=86.242436，B0=86.085607，J0=86.244777；当前候选均未通过原主要gate。语义独立增量不足；selected频率筛选通过但fixed8000空间错配增量不足；DSM独有正确保留相对X−0.919307pp。不宣称新贡献，不追加D26训练。

D27代码接口错误已修，实际CPU转移/strata/输入长度和Python3.10检查通过，新增完整模型回归本轮未执行，CUDA未验证。原十组授权仍有效，修复补跑用新目录，尚无补跑启动观测。GPU0/1 H10080GB、资源充足、nohup/zzx不变，Test6禁读。


用户本次要求下已组织[D27补跑与D28压力评价](../protocols/D27_D28_LINKED_RESEARCH_PLAN_20261003.md)，机器可读plan/16输入case/224 tile预算/边际配对设计校验完成。D28评价代码与后接controller未实现，不能称运行；D29条件4组未冻结、未启动。最新服务器状态仍上文，不因文档更新推定D27已补跑。
