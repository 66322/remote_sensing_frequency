# 共享入口：T队列继续，已准备GPU0机制诊断后继

2026-10-11用户补充：原T实验可能已全部完成，要求结合整轮结果再规划。GitHub回查仍为bce81d59f2fd188a5e500354c4c93be8b7771937，仅T0—T4原件；T5—T9及最终screen未上传，不能确认新完成状态。以下26项为已实现的候选后继，尚未登记；先接收完整T记录，再决定是否原样采用，不把部分证据规划当作全轮结论。

最后服务器证据仍为2026-10-10T21:28:41.841837+08:00，原T队列RUNNING_T5；T0—T4已收原件，T5运行、T6—T9待运行，固定T7未收。这是历史观测，不是实时查询。旧Post-S1最后观测2026-10-10T08:13:57.270242+08:00，已完整结束。

新后继POST_T_MECHANISM：READY_NOT_REGISTERED。26项固定推理（16模块包组合＋10个已有4000步checkpoint），296个模型×条件×tile单元，新增优化器更新0，仅GPU0。代码已实现、11项CPU检查通过；135个继承Python文件与原执行manifest核对一致，真实GPU/权重验收留服务器。尚无新目录/PID/执行回报。

旧上下文四配对+1.614～+2.844pp、新T1/T3匹配上下文约+1.436/+1.432pp，两tile正；上下文问题与部分解决已有开发证据。固定P7=83.575357%，T1/T3=83.856616/83.858189%，均低于R0=85.001650%；T3−T1仅+0.001573pp且tile异号，尚无额外迁移支持。上述仅Potsdam fit12→Val2 3_11/5_10、seed42、固定8000、native512/stride256、NoBoundary mIoU_fg5。

按[研究决定](current/RESEARCH_DECISION.md)→[交接](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)→[实验索引](experiments/rebuild_v1/INDEX.md)读取。GitHub同分支为共享权威。

用户2026-10-10授权规划并挂在当前队列后自动运行；[冻结后继协议](protocols/POST_T_MECHANISM_GPU0_20261010.md)。用户终端执行新enqueue一次后，它等待原T全部完成、进程退出与锁释放，再自动串行推理。原T门槛/运行不变；本次未替服务器登记。完成诊断后不自动启动新训练。主问题与旁支角色保持。

