# 当前交接：M2长程设计已登记，尚未实现/启动（2026-10-16）

先读[研究决定](RESEARCH_DECISION.md)、[M2完整计划](../protocols/PHASE3_M2_ERROR_CORRESPONDENCE_20261015.md)及[下一步](NEXT_EXPERIMENT.md)。用户要求根据完成结果安排GPU0/1长期实验，时间不限；优先研究问题与创新性。

M1与Phase2.4均已结束并验收。M1结果归档09fb57a6ec26f6367c9891f2aa924cc4bf7219cc；11主训练176k，幅度门禁false，down4补救条件失败。关闭旧幅度配方，不重新bootstrap、恢复或上传。原科学结论与辅助证据缺口见[验收](../experiments/PHASE3_M1_ACCEPTANCE_AND_ROUTE_REVIEW_20261015.md)。

本次新问题：错误位置对应性是否提供跨tile、跨RGB实例、跨退化的新增可兑现补救。核心3fold×3整系统seed×(1RGB参考+4交叉拟合RGB教师+7DSM臂)=108个32k训练，3.456M更新。普通CE、自身难例、clean教师、故障教师、分层打乱、熵排序、直接融合目标全比较。固定概率融合及α曲线/margin诊断并报，避免把动作限制误判为无信息。

后续反向最多90训练，第二编码器预留81，总cap279/8.928M；受G0–G4和实现冻结约束。此处是设计，无新执行入口、run/PID或服务器状态。下一任务是落实M2执行包和仅Fit12元数据fold锁，不重复研究旧M1输入配方。

最重要边界：旧全Fit12微调权重不得泄漏进新外层模型或teacher；Val2不进新队列；Test6/held4/final禁读；三fold仍是同城开发CV。RGB–DSM主线与恢复旁支角色不变，创新性未由计划数量确立。另一篇点云不混入。服务器由用户执行，GPU仅物理0/1；RAM用后回收，无整轮磁盘logit缓存。

本次也修正旧NEW_CHAT_HANDOFF_20261015仍写“M1待启动”的过期入口；旧文本保存于docs/history/20261015_before_phase3_m2_plan/。原GPU2–7进程归属仍不明，不操作。
