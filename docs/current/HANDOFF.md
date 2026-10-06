# 当前交接：N5已登记，查询既有队列

最后服务器登记回报（用户终端，2026-10-06）：N5_QUEUE_REGISTERED，目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_n5_20261006T114819_71934，controller PID72265，TRAINING_JOBS=4，GPU0/1，NEW_STEPS=32000；nohup_20261006T114827023329.log。目录时间标记11:48:19、日志名11:48:27，不替代queue observed_at。未收到queue状态、controller/worker存活、mask进度或CUDA首步，不能声称正在训练。下一步只读查询这条N5，不重复登记或重启旧队列。

## 本次接收与立即下一步
科学执行提交2e565cca04d84d8605a96105d12fb6c0871e464d不变。登记确认服务器入口完成来源检查及CPU检查后发起nohup（按已发布执行链推断，独立cpu_checks.log尚未回读），不等于CUDA训练成功。[登记转录](../../records/research_post_n5_20261006T114819_71934/registration_observation.json)。

先运行该目录code/scripts/status_post_n5.py，查看nohup与preparation.log。若PREPARING_MASKS，CPU生成44个整tile掩码阶段可能尚未使用GPU；只有实际状态能确定。出现CONTROLLER_INTERRUPTED/HOLD则先保留日志与worker身份，明确恢复，不自动重训。无需重新git fetch/安装/登记N5。

## 研究与执行边界
可行性探索，RGB–DSM双向条件互补与退化/缺失分割主线，恢复旁支。N2固定gate失败去留保持；N5沿E1问题证据四组匹配控制，固定N1-2完整state，新8000步/组，seed42/batch16。共同native512新增槽、精确25%缺失，T不训练/选模。四组完成后接收原件、按固定gate分析，再准备N3及其余条件族，不自动全跑21组或未实现占位项。

只GPU0/1、每卡一worker、nohup；全部快照/临时/记录在zzx独立目录；用户执行终端，无SSH/重复资源审计、新seed/Test6/independent final或失败配方重跑。代码CPU15项与语法11文件仅就绪验证。登记没有新的实验结果。

[下一步](NEXT_EXPERIMENT.md)；[协议](../protocols/POST_N5_EXECUTION_20261006.md)；[验收结果](../experiments/POST_N2_E0_E1_E2_RESULTS_20261006.md)；[扩展规划](../protocols/POST_N2_EXPANDED_PORTFOLIO_20261006.md)；[上一交接](../history/HANDOFF_PRE_N5_REGISTRATION_20261006.md)。
