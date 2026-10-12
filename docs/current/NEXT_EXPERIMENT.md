# 下一实验：查询已登记Phase1.5，完成后接收原件

## 最新观测：修复版CPU准备中（2026-10-12 23:38）

用户终端只读查询 **QUERY_OBSERVED=2026-10-12T23:38:10.393107+08:00**；queue **LAST_OBSERVED=2026-10-12T23:38:08.675078+08:00**，**PREPARING_FIXED_CACHE_AND_MAPS**，**CONTROLLER_LIVE=True**，100批全部PENDING。原nohup tail无新输出/错误回报；这不单独证明准备完成或真实smoke通过。当前是固定缓存与映射准备，尚无GPU工作进度；显卡空闲符合该阶段。以上是最后观测，不代表实时状态。

修复执行commit `45138f0f92c668bc86ce9532a4382b38d2b12b6d`，原新目录 `research_phase15_recoverability_20261012T233532_842792`、登记PID843079、日志 `nohup_20261012T233542741074.log` 保持；旧路径错误目录继续保留。GPU0/1、0训练、100工作批次、1540唯一逻辑case固定；准备成功后自动GPU0 smoke→GPU1一致性检查→全PASS才双卡全量。无24h总截止。24–48h为资源预留，准备耗时/真实case步速尚未收到，不能给实测剩余ETA。

下一步继续既有控制器，稍后仅读取同一status/nohup；如准备迟迟不变，读 `preparation_progress.json` 与 `logs/prepare_phase15.log` 定位，不重复登记/重启/绕过smoke。不新增训练/seed，不访问Test6/held4/final。五项完整原件上传后再科学验收与选路。

[本次用户进度原件](../../records/research_phase15_recoverability_20261012T233532_842792/user_reported_preparation_20261012T233810.json)。

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

[执行协议](../protocols/PHASE_1_5_EXECUTION_20261012.md)、[完整设计](../protocols/PHASE_1_5_RECOVERABILITY_20261012.md)、[双卡规划](../protocols/PHASE_1_5_TWO_GPU_PLAN_20261012.md)、[CPU验证记录](../../records/phase15_execution_design_20261012/validation.json)。

## 固定矩阵
E CPU复用120旧S1 block-like预测；A S1/R16×4DSM×4mask×20×2tile=1280 missing；B新增80比例case、M25复用；C复用全部CM/新错恢复计数；D补S1-3 160与legacy DSM2，其余复用。另匹配参考及S1熵补全，100批/1540逻辑case、最多1538新完整tile推理；真实smoke额外同case重复另记工程开销。

## 服务器操作
本次固定commit bootstrap已登记，后续复用返回目录；入口自动准备→真实smoke→双卡全量。不得重复登记。真实权重/CUDA尚未回传核验；失败停止并保留原件。

返回DIR后只读：PY -B DIR/code/scripts/status_phase15.py --directory DIR。
完成或HOLD且所有child退出，前台轻量上传：PY -B DIR/code/scripts/upload_phase15.py --directory DIR --root ROOT；给提交号即可，长输出不需粘贴。

不自动训练router/adapter/DSM-only，不追加seed/realization，不改旧gate，Test6/held4/final关闭。24h未完继续；技术单worker6h/DCPU24h超时是失控检测，不是全队24h截止。

登记原始回报：[轻量摘录](../../records/research_phase15_recoverability_20261012T232212_836118/registration_observation.json)。下一步只读 `PY -B DIR/code/scripts/status_phase15.py --directory DIR` 与原nohup日志；进度未收前不认定双卡已开始。
