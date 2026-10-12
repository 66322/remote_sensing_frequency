# 当前研究决定：先做可恢复性分解（2026-10-12）

## 最新登记：路径修复版已接管，进度待查询

2026-10-12用户终端返回 `PHASE15_TECHNICAL_REPLACEMENT_OF` 原失败目录 `research_phase15_recoverability_20261012T232212_836118`，随后 `PHASE15_REGISTERED`。修复执行commit `45138f0f92c668bc86ce9532a4382b38d2b12b6d`；新目录 `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase15_recoverability_20261012T233532_842792`，登记PID843079，日志 `nohup_20261012T233542741074.log`。当前证据状态 **REGISTERED_PROGRESS_NOT_YET_QUERIED**；目录23:35:32与日志23:35:42.741074仅命名时间标记，不是queue observed_at。无controller/worker存活确认、真实smoke结果或科学结果。

接管入口拒绝旧进程存活/锁未释放/原状态不符，由成功登记执行链推断这些检查与服务器同包22项CPU成功返回；检查日志和旧失败snapshot哈希尚未独立接收。原失败目录保留，不复用其case缓存。新执行仍GPU0/1、0训练、100工作批次、1540唯一逻辑case，两卡真实smoke全PASS后自动派发固定全量，无24h总截止；24–48h为资源预留，不是实测剩余ETA。

下一步只读新目录 `code/scripts/status_phase15.py --directory DIR` 与上述nohup日志。不得再次bootstrap/enqueue，旧目录HOLD仅作历史失败证据。五项诊断完整上传后独立验收，再决定配对训练候选；不自动新增训练/seed或访问Test6/held4/final。

[新接管登记原件](../../records/research_phase15_recoverability_20261012T233532_842792/registration_observation.json)。

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


两轮旧实验已上传并验收：Post-T最后上传观测2026-10-12T11:03:22.917566+08:00，8/8 COMPLETE、PAIRED_SCREEN=False；Structured最后上传观测2026-10-12T16:32:44.762198+08:00，42/42 COMPLETE、NO_SUPPORT_THIS_PROTOCOL。这些是历史上传快照，未查询当前服务器实时进程。

R16−H16=+0.348562pp，两tile正，局部门槛通过；总失败来自5/6 E条件相对R0底线。独立8k/16k预算未支持盲目续训，但R16自身8k→16k仍+0.618217pp，不宣称后半程不学习。S1主PE=+0.122522pp、CI跨0，RGB-only PE=+3.119077pp；S1约21pp为缺失区伤害。跨模型差不单独证明DSM因果补偿；R16固定模型特征内容干预提供更直接线索。

## 研究角色与决定来源
主线仍是RGB–DSM双向条件互补与退化/缺失分割；任务驱动恢复旁支。已存在Phase1.5冻结协议，本次用户提交其审查意见并要求结合论文安排GPU0/1、至少一天且未完继续；随后取消本轮对单卡释放的关注。助手据此提出执行前v1.1澄清、约1538次完整tile推理的双卡24–48h资源规划。资源授权不是对新方法有效性的认可。

唯一下一科学问题是RGB局部缺失的可恢复性分解。Phase1.5全程零训练，A DSM对应干预、B nested剂量、C类别、D专家互补与可观测信号、E距离profile。旧Structured位置脆弱性gate不重开。

可靠性/routing从“下一默认方法”改为条件候选，理由：D27/D30旧失败未被新总负gate消除，现有oracle/可识别性证据仍不足。残差context也需诊断，不凭名称或小oracle自动入场。此为明确研究顺序/候选角色修订，不改主线或历史结论。

## 决策边界
raw五expert完整NB headroom的2/6pp保留为资源分流阈值，不是统计定理；高oracle还需部署可得信号下跨tile的专家偏好和超过最佳单专家的空间。旧DSM-only legacy限制与不完整池必须明示。GT class/真实mask解释不是可部署可学习性证明。

不采纳无证据的<2 GPU小时、单realization估方差、zero-init训练后恒等保护及“必然可发表”；完整分歧与修正写入双卡规划。未来四组残差或四组router只为条件设计储备，未登记、未实现，不自动训练。

[双卡具体规划](../protocols/PHASE_1_5_TWO_GPU_PLAN_20261012.md)、[Phase1.5主协议v1.1](../protocols/PHASE_1_5_RECOVERABILITY_20261012.md)、[文献映射](../literature/PHASE_1_5_METHOD_CANDIDATES_20261012.md)、[关键原件复核](../experiments/LATEST_RESULTS_KEY_REVIEW_20261012.md)。

## 2026-10-12执行落实
2026-10-12用户终端已返回 **PHASE15_REGISTERED**，登记时证据状态为 **REGISTERED_PROGRESS_NOT_YET_QUERIED**。执行commit `7b12fec6d7fb451e09316ba59f7d62ca8e0c316b`；目录 `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase15_recoverability_20261012T232212_836118`，登记controller PID836482，日志 `nohup_20261012T232227296552.log`。目录23:22:12与日志23:22:27.296552仅为命名时间标记，不是queue observed_at；尚无只读进度查询、controller/worker存活确认或真实smoke结果。

GPU0/1、100工作批次、1540唯一逻辑case（两S1 clean缓存复用，按最多1538新tile推理计），0训练/0优化器更新。24–48h为预留范围，非当前剩余ETA；无24h总截止。登记前同包CPU检查成功返回由入口执行链推断，服务器cpu_checks.log尚未单独接收；本地20项合成CPU检查及13新Python语法通过不等于真实CUDA/权重验收。

启动入口enqueue_phase15.py幂等检查旧完成队列/锁，继承immutable源码→CPU检查→准备→GPU0真实smoke(ID1/tile3_11)→GPU1同case一致性→自动技术验收全PASS→双卡全量→五项汇总。任一技术失败HOLD且停止拥有的children，不自动retry或加训练。用户终端执行、无SSH，全部记录/缓存/临时产物在/home/jovyan/zzx新目录。

保留原科学问题和主线角色；状态已由发布就绪转为REGISTERED_PROGRESS_NOT_YET_QUERIED。用户授权落实整套执行，技术smoke自动验收并接续固定全量；五项结果齐全后的科学复核/方法选路仍独立进行。

[执行协议](../protocols/PHASE_1_5_EXECUTION_20261012.md)、[完整设计](../protocols/PHASE_1_5_RECOVERABILITY_20261012.md)、[双卡规划](../protocols/PHASE_1_5_TWO_GPU_PLAN_20261012.md)、[CPU验证记录](../../records/phase15_execution_design_20261012/validation.json)。

登记原始回报：[轻量摘录](../../records/research_phase15_recoverability_20261012T232212_836118/registration_observation.json)。下一步只读 `PY -B DIR/code/scripts/status_phase15.py --directory DIR` 与原nohup日志；进度未收前不认定双卡已开始。
