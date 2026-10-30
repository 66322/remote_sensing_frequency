# 当前交接：D26已判定，D27十组需技术修复补跑

更新2026-10-03。研究仍可行性探索，主问题RGB–DSM双方条件互补及退化/缺失可靠分割。D26九组已完成，按原冻结规则关闭XSF/XS/XF本轮确认路径；整个问题不关闭，恢复C1仍旁支，D27:C1是类别路由任务。

[完整复核](../experiments/D26_COMPLETE_D27_FAILURE_REVIEW_20261003.md)：D26原件d3f264182f9ec8d76b1d6df4972d410fb74686f0，D27原件f3d2be839d4f7f73da4389ad49d2524402c62b6c。D26最后观测2026-10-03T04:04:45.239849+08:00 COMPLETE9/9；180份主条件tile矩阵重算与汇总一致。XSF对B0 S+0.156829低于+0.2，语义未过，selected频率有信号但fixed8000错配对照+0.073522不足，DSM独有正确保留相对X−0.919307。强普通融合保留，不重训/改门槛。

D27最后观测2026-10-03T04:12:45.117489+08:00 COMPLETE_WITH_TECHNICAL_FAILURES，0/10；04:05实际接力，十组全部step0失败，无科学结果。run入口过滤tensor字典丢掉treatment字符串列表，objective读字段报KeyError。旧“仍WAITING/待上传”过期。本次修复training_batch保留字段并校验长度；原数据/损失/预算/专家/gate不变。实际CPU接口检查通过，新增完整模型回归尚未执行，服务器补跑未观测。

原十组已获用户授权，必要接口修复后新目录research_d27_safe_routing_repair_<stamp>补跑，不改变原失败快照、不用旧resume跨commit、不重跑D26。具体一次nohup命令见[NEXT](NEXT_EXPERIMENT.md)。运行前已有launcher会检查GPU进程防冲突，不加资源预算审计。保留新运行与旧失败索引，后续原轻量上传。

服务器由用户执行，无SSH；工程/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro。D26原目录research_d26_bidirectional_20261002T191253_1513109；D27原失败目录research_d27_safe_routing_after_d26_20261002T191253_1513109。仅GPU0/1 H10080GB，RAM/磁盘充足，batch16无累积，nohup，所有产物在zzx对应目录。

[假设复核](../experiments/ASSUMPTIONS_AND_RESEARCH_OPPORTUNITIES_20261003.md)仍是候选，先获得D27有效比较；安全/MoE/局部类别路线未被技术失败判定。Test6禁读，Val2/历史held4不独立；权重/预测未上传，服务器索引不等于实际收到本体。[前交接](../history/HANDOFF_before_D26_D27_results_20261003.md)。
