# 共享入口：D27结论已复核，D28待结果，D30后接计划

权威分支：rebuild-v1-protocol-20260915。2026-10-03更新。

先读[研究决定](current/RESEARCH_DECISION.md)→[交接](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)。

研究仍处可行性探索：RGB–DSM双方条件互补、任一模态退化/缺失可靠分割。频率和专家是候选解法，任务驱动恢复仍旁支，未决定转向或冻结论文贡献。

D27修复轮已完成10/10并上传cedbc594d4e438d3c220ee80d3e82f563a8c2ae3，500份tile原件复核支持当前四gate失败。保护/恢复使综合下降约1.8pp；DSM独有正确保留增加伴随更大的RGB正确计数损失；动态/局部/类别增量不足。known missing回退成立但不代表未知失效鲁棒性。证据限开发Val2/seed42，不能扩大为研究问题失败。

D28最后收到的服务器观测为2026-10-03T18:34:10.615615+08:00：RUNNING、0/7，RGB_anchor在GPU0、DSM_anchor在GPU1。尚未收到更晚状态，不能推定当前完成。既定七模型、238次tile评价继续，禁止重复启动。

用户最新要求根据完成实验规划新增后接队列。建议[D30损失拆解](protocols/D30_LOSS_DECOMPOSITION_AFTER_D28_20261003.md)：48次checkpoint重放＋4组静态融合训练，复用S0/S1。**仅规划，尚未实现/排队/启动**；原D29未激活。此变化是新增诊断设计，不恢复D27失败门槛。

[D27完整复核](experiments/D27_FINAL_REVIEW_20261003.md)、[机器计划](../records/research_d30_plan_20261003/plan.json)。服务器由用户终端操作，无SSH。仅GPU0/1，两卡H10080GB；RAM/硬盘充足，无资源审计。物理batch16无累积；长任务nohup，所有快照/临时/缓存/日志在/home/jovyan/zzx相应实验目录。Test6禁读，开发Val2非独立final。GitHub此分支为共享权威，权重/预测本体服务器保留索引。

旧入口已[原样归档](history/pre_D30_plan_20261003/START_HERE.md)，其中启动初期状态不再代表当前记录。
