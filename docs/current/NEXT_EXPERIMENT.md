# 下一步：只读查询已登记N5，避免重复启动

## 2026-10-06掩码准备观测

用户只读回报（2026-10-06）：queue LAST_OBSERVED=2026-10-06T11:48:28.739479+08:00，PREPARING_MASKS，controller PID72265 LIVE=True；N5四组PENDING、0/8000、worker PID−1。queue时间是进入CPU准备阶段时刻，不代表日志后续进度时刻。preparation.log已有13个唯一tile的N5_MASKS_COMPLETE，fit12全部12个及Val2 3_11已报告，预定5_10尚无完成行；未收到精确日志时间/准备完成标记/worker首步，未见本回报错误。准备结束自动派发GPU0 N5-0、GPU1 N5-1；只读继续观察，不重复启动。


最后服务器登记回报（用户终端，2026-10-06）：N5_QUEUE_REGISTERED，目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_n5_20261006T114819_71934，controller PID72265，TRAINING_JOBS=4，GPU0/1，NEW_STEPS=32000；nohup_20261006T114827023329.log。目录时间标记11:48:19、日志名11:48:27，不替代queue observed_at。未收到queue状态、controller/worker存活、mask进度或CUDA首步，不能声称正在训练。下一步只读查询这条N5，不重复登记或重启旧队列。

服务器目录：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_n5_20261006T114819_71934
只读入口：该目录code/scripts/status_post_n5.py --directory <同目录>，使用D21 plan中绑定python。查看nohup_20261006T114827023329.log及存在时preparation.log；需要时cpu_checks.log。不要再次运行enqueue、不要重启N1/N2/诊断。

控制器正常应先PREPARING_MASKS再RUNNING_N5。准备在CPU生成fit12 U/H/L及Val2 U/H/L/T，共44个整tile掩码；此时GPU空闲可能正常，但没有日志前不作此断言。真实CUDA首步及controller/worker存活待本次查询确认。

四组结束N5_COMPLETE_AWAITING_REVIEW后上传轻量原件，按冻结gate决定后继；技术故障先查询worker存活/日志并明确接管，不自动重训。全部旧路线去留与N3/R1/N4/R2条件门槛保持。本次登记不是21组已派发。

GPU0/1、nohup、zzx记录、用户终端无SSH；无Test6/independent final/held4、新seed或重复资源审计。[执行协议](../protocols/POST_N5_EXECUTION_20261006.md)、[交接](HANDOFF.md)。
