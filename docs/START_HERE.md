# START HERE：D27后接队列已实现，服务器启动观测待回传

2026-10-02；权威分支rebuild-v1-protocol-20260915。读[研究决定](current/RESEARCH_DECISION.md)→[交接](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)。

最后上传的服务器观测仍为2026-10-02T22:22:14.689169+08:00：D26 RUNNING、COMPLETE1/9；没有更新实时PID信息。 [B0部分证据](experiments/D26_B0_PARTIAL_REVIEW_20261002.md)支持总体融合有益但局部存在伤害，尚无新机制确认。

用户已授权十组D27接在D26后自动跑。[方案](protocols/D27_SAFE_ROUTING_PLAN_20261002.md)、[执行说明](protocols/D27_SAFE_ROUTING_EXECUTION_20261002.md)、[固定plan](../records/research_d27_plan_20261002/plan.json)、[验证](../records/research_d27_plan_20261002/local_validation.json)已就绪：十组×8000、两GPU、batch16、无累积、nohup。新后台controller等待原九组结束及controller锁释放；无需手动切换。尚无实际服务器排队/启动观测，不能把准备写成正在训练。

研究安全融合→动态专家→局部/类别适配，双方信息保留。复用原单模态专家，固定遗传源码52f94388，新代码随本次执行commit锁定；不重训单模态、资源探针或修改D26。所有服务器产物在zzx对应独立目录。D23/D25失败配方关闭，恢复旁支角色不变，Test6禁读，开发证据不当独立final。近期论文角色见[映射](literature/D27_SAFE_ROUTING_RECENT_LITERATURE_20261002.md)。
