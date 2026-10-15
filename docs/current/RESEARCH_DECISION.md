# 研究决定：按已登记Phase3-M1落实；新机制仍待实验（2026-10-15）

Phase3-M1已按用户要求落实执行包，尚未取得服务器启动回执。仅使用本篇遥感RGB/DSM/标签，GPU0/1，固定16k、batch16；11个新主训练，最多2个条件反证，总上限13个新训练208k更新。旧M00/42在绑定合格时复用，Test6/held4/final不读，点云论文不进入本轮。

双卡共享就绪队列，空闲卡可以领取另一seed任务。GPU到CPU交接只等内存接收，不等计数完成；RGB故障前向跨所有DSM对照共享。Fit训练RAM在全部训练消费者结束后分进程释放，条件预测匿名RAM在最后计数消费者结束后关闭，成功作业的滚动优化器在端点与主计数核验后退役。GPU无后续任务时先退出，CPU继续收尾；所有自有进程退出后清理runtime cache/temporary。负结果、失败恢复状态、必要16k权重和充分整数证据保留。

[执行与清理协议](../protocols/PHASE3_M1_EXECUTION_20261015.md)；[科学设计](../protocols/PHASE3_M1_DESIGN_20261015.md)；[包清单](../../configs/phase3_m1_execution_manifest.json)；[本机检查记录](../../records/phase3_m1_implementation_review_20261015.json)。

首要对比M21−M11，区分统一相对高度幅度与普通稳健归一化；A1−A0区分普通输入适配。DSM独立精度、对固定RGB错误的补救容量、固定融合实际救回/损伤分别报告。普通处理解释改善时按普通解释收口，无稳定幅度效应则跳过条件反证。不是把解冻本身包装成创新。

用户已要求按这份设计落实执行；真实质量观测A与另一篇点云论文不进入本轮。原RGB–DSM条件互补主线与恢复旁支角色保留。两张反复开发Val2、两DSM seed和单个固定RGB seed不提供独立地理泛化。

执行协议明确固定融合使用Phase2.4式FP64 post-stitch累积logit混合，数值实现对全部新组一致，区别于设计文字中的逐窗口混合舍入。旧门禁不变。[原验收](../experiments/PHASE_24_ACCEPTANCE_AND_ROUTE_REVIEW_20261015.md)。
