# 当前交接：TS目录冲突已确认，保留TF的GPU0恢复入口已交付

更新2026-10-01，用户回传TS日志确认RuntimeError: refuse existing output directory，位置run_rebuild_v1_d23.py:24。根因是接续启动器在无checkpoint时提前创建新输出目录；27789b2已修复此缺陷，11项队列检查通过。

TF最后观测为GPU1 PID815379，在后台controller PID815309的日志elapsed_minutes=2.0进入训练step1；本次TS错误回传没有新的TF步骤/完成证据和墙钟。TSF/T0既有4000步及评价完成保留，整八组尚未完成。

新增recover_rebuild_v1_d23_gpu0.py，可在保留TF执行的同时恢复GPU0 TS。入口核对失败队列、现有工作进程与执行绑定，使用本次目录独占恢复锁；不向既有TF或controller发送信号。若TF仍活跃，只启动TS；TS成功且TF与旧controller退出后，合并TS完成记录，再交给固定接续队列补剩余四组。若TF已完成且controller退出，直接普通双卡接续。若TF停止但无完成标记、TS恢复失败或状态发生冲突，停止新增任务并保留证据，不盲目重跑。恢复事件、TS日志、新执行快照、PID和nohup日志均在原zzx实验目录。

本地新增5项恢复检查通过，加上11项队列检查共16项；模拟覆盖TF运行/已完成两条路径、无重复TF、保留日志、异常状态及完成标记。服务器恢复尚未执行/观测，不声称GPU实测提速或全部完成。此为启动/调度修复，不混入prefetch开发；worker/model/engine/runtime lock和科学协议均未修改。

研究仍为频率＋语义可靠性与RGB–DSM退化/缺失融合可行性探索；C1旁支、部分解冻强基线，冻结阈值和Test6禁读不变。下一步由用户nohup执行恢复入口，助手核对启动短输出；结束后上传八组轻量原件再作机制/风险分析。资源持续为GPU0/1两H10080GB，主机内存/磁盘充足；没有新增预算或smoke轮次。
