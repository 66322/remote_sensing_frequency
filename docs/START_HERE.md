# 共享入口：旧Post-S1完整分析，GPU0后继T0—T4部分验收

截至收到的原件：旧阶段最后观测2026-10-10T08:13:57.270242+08:00，SUPPORT_COMPLETE_AWAITING_REVIEW；新阶段最后观测2026-10-10T21:28:41.841837+08:00，RUNNING_T5。上传成员T0—T4；T5运行、T6—T9待运行，固定T7尚未收到。仅GPU0；这是历史观测，非实时服务器查询。

旧十P全部完成。四个上下文匹配对RGB_U增益+1.614～+2.844pp且两tile均正；固定P7=83.575357%，比R0=85.001650%低1.426292pp。旧E形状检验通过、整体P7=False，Q跳过。P3=84.399508%也未达到R0路线底线。

新T1/T3=83.856616/83.858189%，匹配上下文收益+1.436170/+1.431901pp；T3−T1仅+0.001573pp，逐tile一正一负，未支持S1-1额外迁移收益。两者仍低于R0约1.145/1.143pp。T0—T4底座/支持外保护与常规条件一致；固定T7/随机控制未收到，整轮科学门槛尚不能裁决。

所有数值是Potsdam fit12→Val2=3_11/5_10、seed42、固定8000、NoBoundary mIoU_fg5的开发结果。不是独立最终检验或双向有效承诺。完整口径、绑定、原件与审计边界见[结果报告](experiments/POST_S1_FULL_TRANSFER_PARTIAL_RESULTS_20261010.md)。

按[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)→[实验索引](experiments/rebuild_v1/INDEX.md)读取。GitHub同分支为共享权威。

继续已注册GPU0队列，不重复enqueue、不重训P、不新增seed、不触发Q。下一次接收完成T记录，按预定T7−T1/T6/T9、R0、保护及六E验收。路线角色不变。
