# 下一实验：查询已登记Phase1.5，完成后接收原件

2026-10-12用户终端已返回 **PHASE15_REGISTERED**，当前证据状态为 **REGISTERED_PROGRESS_NOT_YET_QUERIED**。执行commit `7b12fec6d7fb451e09316ba59f7d62ca8e0c316b`；目录 `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase15_recoverability_20261012T232212_836118`，登记controller PID836482，日志 `nohup_20261012T232227296552.log`。目录23:22:12与日志23:22:27.296552仅为命名时间标记，不是queue observed_at；尚无只读进度查询、controller/worker存活确认或真实smoke结果。

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
