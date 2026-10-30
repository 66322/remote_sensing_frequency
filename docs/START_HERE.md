# 当前入口：Full已有正式更新，补齐空间头自动接续（2026-10-30）

先读[研究决定](current/RESEARCH_DECISION.md)、[交接](current/HANDOFF.md)、[状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)。长期约定见[AGENTS](../AGENTS.md)、[执行约定](protocols/EXECUTION_CONTRACT.md)、[规划规则](protocols/EXPERIMENT_PLANNING_RULES.md)和[启动/首败控制](protocols/STARTUP_DELIVERY_AND_FAILURE_CONTROL.md)。

最后实际观测：2026-10-30 19:38:20+08。Full GPU0 Q2/3000、GPU1 G1/1100，已有真实优化；七条轻量profile通过。B0/B1/Q1/S1已返回8k训练循环，至少36,100次Full更新为源码/派发推断下界；完整科学分数及S1资格结果尚未回传。[原始观察](../records/post_m2_multiroute_v2_20261030_r1/progress_observations/20261030T193820/observation.json)不冒充当前实时存活。

原A0已在19:01完成两模型各2k及校准/外层，14份小JSON和原始计数已验。校准DINOv3 +1.6257pp、outer开发−0.6527pp，保留原校准READY，不事后加门槛。[完整A0复盘](experiments/POST_M2_A0_RESULTS_AND_REVIEW_20261030.md)。旧IPC故障16个确认进程已停止，无残留回执；旧失败证据保留，不重跑旧入口。

当前Full冻结d15载荷和控制器保持，不再运行bootstrap/repair。原入口只自动覆盖11项Full；两空间读出曾独立、没有接入队尾，现由[外置单次接续](experiments/POST_M2_A_SPATIAL_FOLLOWUP_20261030.md)补齐。新空间头接续入口已发布并完成本地17项检查，尚未收到服务器注册、profile或正式更新回执。不能写成已入队。唯一注册命令见[下一步](current/NEXT_EXPERIMENT.md)，无须逐phase手工操作。

接续程序等待Full正常结束和GPU0/1释放，不等上传、不修改Full冻结文件；随后每卡一个常驻进程，复用骨干与拟合图块，按原预算完成两空间头各2k及条件评价。原A0/骨干加载检查复用，只有两个新读出各4步轻量检查。首批仍15作业/96k/seed42，无新增科学预算。

研究主线不切换。A1/A2、C/P/E/F、频率子实验各有前置，未入队；不把代码就绪当作实验执行。Val2/Test6/held4/final仍封存。M2已验收、DF配方关闭，J工程停止；最终清理仍暂缓，最后确认18端点，无成功最终删除回执。
