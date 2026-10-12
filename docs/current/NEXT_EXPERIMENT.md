# 下一实验：Phase1.5执行包READY_NOT_REGISTERED

2026-10-12用户“按上述规划进行”并“继续”，已落实Phase1.5独立执行包。**READY_NOT_REGISTERED**：本地20项合成CPU检查与13新Python语法通过，尚无服务器登记/PID或真实权重/CUDA结果。GPU0/1、100工作批次、1540唯一逻辑case（两S1 clean缓存复用，按最多1538新tile推理计）；0训练/0优化器更新，24–48h预留且无24h总截止。

启动入口enqueue_phase15.py幂等检查旧完成队列/锁，继承immutable源码→CPU检查→准备→GPU0真实smoke(ID1/tile3_11)→GPU1同case一致性→自动技术验收全PASS→双卡全量→五项汇总。任一技术失败HOLD且停止拥有的children，不自动retry或加训练。用户终端执行、无SSH，全部记录/缓存/临时产物在/home/jovyan/zzx新目录。

[执行协议](../protocols/PHASE_1_5_EXECUTION_20261012.md)、[完整设计](../protocols/PHASE_1_5_RECOVERABILITY_20261012.md)、[双卡规划](../protocols/PHASE_1_5_TWO_GPU_PLAN_20261012.md)、[CPU验证记录](../../records/phase15_execution_design_20261012/validation.json)。

## 固定矩阵
E CPU复用120旧S1 block-like预测；A S1/R16×4DSM×4mask×20×2tile=1280 missing；B新增80比例case、M25复用；C复用全部CM/新错恢复计数；D补S1-3 160与legacy DSM2，其余复用。另匹配参考及S1熵补全，100批/1540逻辑case、最多1538新完整tile推理；真实smoke额外同case重复另记工程开销。

## 服务器操作
从本次固定commit提取scripts/enqueue_phase15.py，使用绑定d18_dino Python执行 --root ROOT --commit COMMIT。入口自动CPU→真实smoke→双卡全量；已有prefix只报状态不重复登记。真实权重/CUDA尚未核验，失败停止/保留原件。

返回DIR后只读：PY -B DIR/code/scripts/status_phase15.py --directory DIR。
完成或HOLD且所有child退出，前台轻量上传：PY -B DIR/code/scripts/upload_phase15.py --directory DIR --root ROOT；给提交号即可，长输出不需粘贴。

不自动训练router/adapter/DSM-only，不追加seed/realization，不改旧gate，Test6/held4/final关闭。24h未完继续；技术单worker6h/DCPU24h超时是失控检测，不是全队24h截止。
