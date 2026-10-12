# 当前交接：Phase1.5双卡规划已细化，执行包待做（2026-10-12）

两轮旧实验已上传并验收：Post-T最后上传观测2026-10-12T11:03:22.917566+08:00，8/8 COMPLETE、PAIRED_SCREEN=False；Structured最后上传观测2026-10-12T16:32:44.762198+08:00，42/42 COMPLETE、NO_SUPPORT_THIS_PROTOCOL。这些是历史上传快照，未查询当前服务器实时进程。

主线RGB–DSM条件互补保持；当前唯一下一任务为零训练可恢复性分解，不直接训练可靠性gate。已存在主协议，本次把审查和新资源请求合并为v1.1。GPU0/1并行，24–48小时规划窗口，超过一天继续；用户明确本轮不用处理释放单卡。

R16−H16=+0.348562pp，两tile正，局部门槛通过；总失败来自5/6 E条件相对R0底线。独立8k/16k预算未支持盲目续训，但R16自身8k→16k仍+0.618217pp，不宣称后半程不学习。S1主PE=+0.122522pp、CI跨0，RGB-only PE=+3.119077pp；S1约21pp为缺失区伤害。跨模型差不单独证明DSM因果补偿；R16固定模型特征内容干预提供更直接线索。

## 下一步
按双卡规划实现独立执行包，不重复登记旧队列。E/C CPU共享，A/B/D按model/tile分小批动态双卡；核心新增1378＋熵补全最多160完整tile推理。真实smoke id=1，主协议12项及新增checks全部PASS后全量。没有本阶段服务器PID/实时观测，状态PLANNED_AWAITING_IMPLEMENTATION_AND_SMOKE。

## 必须继承
A同DSM clean参考；B无PE、整图/缺失区/共同M5分开；shuffle无padding裁切破坏双射；D完整NB主gate、缺失区辅助，不称严格mIoU上界；legacy DSM限制；ECI分母非正NA；zero-init不是训练后保护保证。所有结论条件于两开发tile，20mask非20独立场景。

未采纳<2GPU小时、一个realization估方差及提前决定可发表方向。未来四组训练只为条件草案，不能自动启动。Test6/held4/final关闭，zzx存档，无SSH。

[双卡具体规划](../protocols/PHASE_1_5_TWO_GPU_PLAN_20261012.md)、[Phase1.5主协议v1.1](../protocols/PHASE_1_5_RECOVERABILITY_20261012.md)、[文献映射](../literature/PHASE_1_5_METHOD_CANDIDATES_20261012.md)、[关键原件复核](../experiments/LATEST_RESULTS_KEY_REVIEW_20261012.md)。
