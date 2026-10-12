# 当前状态：Phase1.5已登记，进度待查询（2026-10-12）

## 最新观测：GPU0 smoke持续推进（2026-10-12 23:46）

最后用户查询 **QUERY_OBSERVED=2026-10-12T23:46:42.157635+08:00**；queue **LAST_OBSERVED=2026-10-12T23:46:40.290014+08:00**，**SMOKE_GPU0 / CONTROLLER_LIVE=True**，100批全部PENDING。progress最后观测23:46:33.902794，case `S1_3_11_intact_01_random_25`、GPU0/inference、529/529窗口、optimizer_updates=0。前两次23:43:25为R16 tile_shuffle clean 424/529，23:46:15为S1 pixel缺失529/529；case变化证明这一观测区间内在推进，不能把同一标签/窗口数当全队完成比例或卡死证据。三次nohup tail均无新输出/错误回报。

529/529仅当前case窗口推理结束，后续尚有计数/记录/缓存和检查。执行链进入random意味着前面pixel replay检查已返回，属于流程推断；尚未收到smoke PASS原件，不能宣布所有模型/条件验收。GPU1在GPU0全部smoke成功后自动同case检查，两份PASS之后双卡全量。以上是最后观测，不是实时查询；GPU1此时未派发符合阶段依赖。

修复执行commit `45138f0f92c668bc86ce9532a4382b38d2b12b6d`、目录 `research_phase15_recoverability_20261012T233532_842792`、登记PID843079、日志 `nohup_20261012T233542741074.log` 保持；旧失败目录保留。固定0训练/100批/1540唯一逻辑case，无24h总截止；没有科学结果或实测全队ETA，24–48h仍为资源预留。

继续既有控制器，稍后只读同一status/nohup，不重复登记、不另启GPU1、不绕过smoke。若后续HOLD，读取对应子日志并保留证据，不自动重试。全部轻量原件齐全后再科学复核、选配对训练候选；不追加seed，不访问Test6/held4/final。

[三次用户进度原件](../../records/research_phase15_recoverability_20261012T233532_842792/user_reported_gpu0_smoke_20261012T234642.json)。

---

## 历史修复记录：已定位路径错误，发布时待接管

用户补充的GPU0子日志定位到 `phase15_inference.py` 输入绑定记录路径：`self.base/'input_binding_last_'+str(self.gpu)+'.json'`，因运算优先级先生成Path再加字符串，触发 `TypeError: unsupported operand type(s) for +: 'PosixPath' and 'str'`。已改为 `self.base/('input_binding_last_'+str(self.gpu)+'.json')`。xFormers提示不是该退出根因；没有smoke通过或方法有效性证据。失败发生在写出case记录之后、返回之前，原partial产物不能当smoke验收通过。

本地22项CPU检查与13文件AST通过，新增实际绑定写入语句的GPU0/1回归、显式接管拒绝条件检查；不等于服务器真实CUDA验证。发布时修复状态 **REPAIR_READY_NOT_REGISTERED**；原目录最后观测仍为SMOKE_FAILED_HOLD、100 PENDING、controller非存活（查询2026-10-12T23:28:06.269038+08:00，queue23:27:34.651175）。新PID/目录未回传。

用户终端使用修复发布commit的enqueue入口及显式 `--replace-path-bug-directory OLD_DIR`。仅允许本次原commit/原目录/已确认错误、全100 PENDING、无GPU1 smoke、无存活controller/stage/E/job且锁释放的替代；只允许一个既有原目录。第二次调用发现替代目录就停止登记。保留旧源码/日志/产物，新技术执行目录记录旧plan/code/status/failure/log SHA，不复用失败case缓存；重做准备/CPU22项/真实smoke，smoke全PASS后继续相同100批/1540唯一逻辑case。不是新科学矩阵、追加seed或自动重试；以后任何新失败仍HOLD不自动接管。原旧队列不重启，不访问Test6/held4/final。

---

## 最后服务器观测（历史回报）：GPU0 smoke失败，停止全量（2026-10-12 23:28）

用户终端只读查询 QUERY_OBSERVED=2026-10-12T23:28:06.269038+08:00；queue LAST_OBSERVED=2026-10-12T23:27:34.651175+08:00，**SMOKE_FAILED_HOLD**，CONTROLLER_LIVE=False，100批全部PENDING。主日志为 `smoke_phase15.py exit=1`，发生在GPU0 smoke子进程；GPU1 smoke及全量未派发。准备脚本成功返回由控制器到达此阶段的执行链推断，不等于独立验收准备原件。主日志未包含子进程根因，不能认定为OOM、权重或矩阵一致性问题；无新科学结论。

执行commit与原目录保持。下一步仅读取原目录 `logs/smoke_gpu0.log`、`technical_failure.json`、`smoke/gpu0/progress.json`（若存在），必要时上传HOLD轻量原件。不得重复enqueue、删除缓存、绕过smoke或自动重试；根因明确后再落实有版本记录的技术修复。旧科学gate及固定诊断范围不变。此前登记/待查询状态为历史。

[用户失败回报](../../records/research_phase15_recoverability_20261012T232212_836118/user_reported_smoke_failure_20261012T232806.json)。

---


2026-10-12用户终端已返回 **PHASE15_REGISTERED**，登记时证据状态为 **REGISTERED_PROGRESS_NOT_YET_QUERIED**。执行commit `7b12fec6d7fb451e09316ba59f7d62ca8e0c316b`；目录 `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase15_recoverability_20261012T232212_836118`，登记controller PID836482，日志 `nohup_20261012T232227296552.log`。目录23:22:12与日志23:22:27.296552仅为命名时间标记，不是queue observed_at；尚无只读进度查询、controller/worker存活确认或真实smoke结果。

GPU0/1、100工作批次、1540唯一逻辑case（两S1 clean缓存复用，按最多1538新tile推理计），0训练/0优化器更新。24–48h为预留范围，非当前剩余ETA；无24h总截止。登记前同包CPU检查成功返回由入口执行链推断，服务器cpu_checks.log尚未单独接收；本地20项合成CPU检查及13新Python语法通过不等于真实CUDA/权重验收。

启动入口enqueue_phase15.py幂等检查旧完成队列/锁，继承immutable源码→CPU检查→准备→GPU0真实smoke(ID1/tile3_11)→GPU1同case一致性→自动技术验收全PASS→双卡全量→五项汇总。任一技术失败HOLD且停止拥有的children，不自动retry或加训练。用户终端执行、无SSH，全部记录/缓存/临时产物在/home/jovyan/zzx新目录。

旧两轮最后上传观测：Post-T 2026-10-12T11:03:22.917566+08:00，8/8 COMPLETE、PAIRED_SCREEN=False；Structured 2026-10-12T16:32:44.762198+08:00，42/42 COMPLETE、NO_SUPPORT_THIS_PROTOCOL。不是当前服务器实时查询。R16−H16+0.348562pp局部门槛通过，总失败来自5/6 E−R0底线；独立预算未支持盲目续训，但R16自身后8k仍+0.618217pp。S1主PE+0.122522pp/CI跨0，RGB-only+3.119077pp；旧gate不改。

科学阶段为零训练可恢复性分解E/A/B/C/D：空间profile、DSM对应干预、比例曲线、类别分解、固定专家互补/可观测信号。可靠性/routing与残差context均为条件候选，下一训练草案未派发。

本地验证只覆盖合成模型/数组/调度/完整模拟汇总；服务器同包CPU成功返回仅由登记执行链推断，日志未单收；真实smoke进度/验收尚未查询。源模型严格保留S1-0/S1-3/R16图，DSM-only使用D15 legacy seed42；zero为existing dsm_present_zero且dm=True。没有Test6/held4/final、新seed、旧配方重跑。

[执行协议](../protocols/PHASE_1_5_EXECUTION_20261012.md)、[完整设计](../protocols/PHASE_1_5_RECOVERABILITY_20261012.md)、[双卡规划](../protocols/PHASE_1_5_TWO_GPU_PLAN_20261012.md)、[CPU验证记录](../../records/phase15_execution_design_20261012/validation.json)。

登记原始回报：[轻量摘录](../../records/research_phase15_recoverability_20261012T232212_836118/registration_observation.json)。下一步只读 `PY -B DIR/code/scripts/status_phase15.py --directory DIR` 与原nohup日志；进度未收前不认定双卡已开始。
