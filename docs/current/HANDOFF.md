# 当前交接：GPU0恢复TS进程已创建，等待训练进度

## 最新恢复启动观测（2026-10-01用户回传）

48ab1e4恢复入口已由用户nohup执行。恢复controller PID834840；GPU0空闲短等待通过，随后D23_RECOVERY_TS_STARTED，TS PID834884。当前只确认进程创建，尚未取得恢复后训练step或完成记录。没有独立回传墙钟；以下文件名中的18:37:00是启动标识，不作为实时存活保证。

恢复controller日志：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d23_b_formal_20261001T152548_658274/nohup_recover_gpu0_20261001T183700_834385.log
TS直接日志：同目录/TS_gpu0repair_20261001T183700466561.log

下一步沿此恢复任务继续，不再次启动。TF保留由旧controller管理，其当前进度未新观测；恢复入口在TS与TF完成且旧controller退出后自动接续剩余四组。需查看训练步骤时只读TS直接日志；结束后按后台提示前台上传轻量原件。此前“恢复尚未执行”的表述现为历史背景，不覆盖本节。

更新2026-10-01，用户回传TS日志确认RuntimeError: refuse existing output directory，位置run_rebuild_v1_d23.py:24。根因是接续启动器在无checkpoint时提前创建新输出目录；27789b2已修复此缺陷，11项队列检查通过。

TF最后观测为GPU1 PID815379，在后台controller PID815309的日志elapsed_minutes=2.0进入训练step1；本次TS错误回传没有新的TF步骤/完成证据和墙钟。TSF/T0既有4000步及评价完成保留，整八组尚未完成。

新增recover_rebuild_v1_d23_gpu0.py，可在保留TF执行的同时恢复GPU0 TS。入口核对失败队列、现有工作进程与执行绑定，使用本次目录独占恢复锁；不向既有TF或controller发送信号。若TF仍活跃，只启动TS；TS成功且TF与旧controller退出后，合并TS完成记录，再交给固定接续队列补剩余四组。若TF已完成且controller退出，直接普通双卡接续。若TF停止但无完成标记、TS恢复失败或状态发生冲突，停止新增任务并保留证据，不盲目重跑。恢复事件、TS日志、新执行快照、PID和nohup日志均在原zzx实验目录。

本地新增5项恢复检查通过，加上11项队列检查共16项；模拟覆盖TF运行/已完成两条路径、无重复TF、保留日志、异常状态及完成标记。服务器恢复尚未执行/观测，不声称GPU实测提速或全部完成。此为启动/调度修复，不混入prefetch开发；worker/model/engine/runtime lock和科学协议均未修改。

研究仍为频率＋语义可靠性与RGB–DSM退化/缺失融合可行性探索；C1旁支、部分解冻强基线，冻结阈值和Test6禁读不变。下一步由用户nohup执行恢复入口，助手核对启动短输出；结束后上传八组轻量原件再作机制/风险分析。资源持续为GPU0/1两H10080GB，主机内存/磁盘充足；没有新增预算或smoke轮次。

最新用户回传（2026-10-01，无独立观测墙钟）：TS_gpu0repair日志已出现D23_GATE_TRAIN TS 1 1.0572699308395386，确认恢复后已执行训练step1。此前“训练步骤尚未取得”是旧观测；TF当前进度未新回传。新增只读查询scripts/status_rebuild_v1_d23.py，覆盖旧队列及GPU0恢复任务，并按既有实际耗时估算ETA。[进度查询说明](../protocols/D23_PROGRESS_QUERY_20261001.md)。

## D23两组已上传结果的研究判断（2026-10-01）

[阶段报告](../experiments/D23_TSF_T0_PARTIAL_RESULTS_20261001.md)：主口径TSF相对R0综合+1.111789pp，但相对M0_safe−0.148998pp，相对T0+0.001578pp；rescue保留62.557%。主要候选TSF已不满足确认门槛。问题主线仍是辅助模态的有益融合/负迁移控制，语义与频率为可去留解法，不承诺模块组合；剩余既定对照继续用于解释机制，不改阈值或追加预算。C1旁支不自动升级。原件784逐tile矩阵/392pooled矩阵的加和与fg5重算通过，非全八组验收。
