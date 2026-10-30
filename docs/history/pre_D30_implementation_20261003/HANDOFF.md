# 当前交接：D30后接方案已设计，未排队

研究仍处可行性探索：RGB–DSM双方条件互补、任一模态退化/缺失可靠分割。频率和专家是候选解法，任务驱动恢复仍旁支，未决定转向或冻结论文贡献。

D27修复轮已完成10/10并上传cedbc594d4e438d3c220ee80d3e82f563a8c2ae3，500份tile原件复核支持当前四gate失败。保护/恢复使综合下降约1.8pp；DSM独有正确保留增加伴随更大的RGB正确计数损失；动态/局部/类别增量不足。known missing回退成立但不代表未知失效鲁棒性。证据限开发Val2/seed42，不能扩大为研究问题失败。

D28最后收到的服务器观测为2026-10-03T18:34:10.615615+08:00：RUNNING、0/7，RGB_anchor在GPU0、DSM_anchor在GPU1。尚未收到更晚状态，不能推定当前完成。既定七模型、238次tile评价继续，禁止重复启动。

## 最新工作与下一步

用户要规划新增队列；[D30协议](../protocols/D30_LOSS_DECOMPOSITION_AFTER_D28_20261003.md)与[机器计划](../../records/research_d30_plan_20261003/plan.json)已整理。48次G0/G1固定路由诊断；4组静态S训练P、R、PR_area、PR_pixel，复用S0/S1，8000步/组，总32000步。两卡两轮约3.5—4.5小时，仅按旧作业估计。

当前为PLANNED_NOT_IMPLEMENTED_NOT_QUEUED。没有D30控制器/PID或启动命令。下一实施需实现并验证目标数值兼容、checkpoint绑定、D28锁释放后接、分项loss/梯度日志；不可宣称已有队列接力。D28科学负结果不阻止独立损失诊断，技术失败则HOLD。原D29不自动启动。

研究边界：D27已经失败的是当前配方和机制，未证明唯一根因；新设计拆开保护、恢复、交互及恢复归一化。仅修复回到S0不构成新贡献；新筛选规则只用于后续资源分配，不修改原gate。未采纳继续堆MoE/频率、自动扫权重、多seed追训、用D28挽救D27等做法。

## 绑定与事实来源

D27运行research_d27_safe_routing_repair_20261003T092243758628_2001983；执行ba7088ec05be7b85dd45e5896a8407506bcca14d；原件cedbc594d4e438d3c220ee80d3e82f563a8c2ae3。[完整复核](../experiments/D27_FINAL_REVIEW_20261003.md)。D28运行research_d28_pressure_20261003T092243758628_2001983，均在工程records下。

服务器由用户终端操作，无SSH。仅GPU0/1，两卡H10080GB；RAM/硬盘充足，无资源审计。物理batch16无累积；长任务nohup，所有快照/临时/缓存/日志在/home/jovyan/zzx相应实验目录。Test6禁读，开发Val2非独立final。GitHub此分支为共享权威，权重/预测本体服务器保留索引。

[前版交接](../history/pre_D30_plan_20261003/HANDOFF.md)。不重做资源审计，不重复启动D27/D28，不把旧失败目录当新repair科学结果。
