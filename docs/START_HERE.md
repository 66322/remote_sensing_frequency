# 共享入口：Post-T已验收，v2实验安排待实现

权威分支：66322/remote_sensing_frequency，rebuild-v1-protocol-20260915。

最后服务器查询2026-10-11T13:48:26.474610+08:00：原Post-T 26/26 COMPLETE，controller/workers已退出，0新训练。原件57ef5ad9已离线验收；这不是实时查询。主线仍RGB–DSM双向条件互补与退化/缺失分割，恢复为旁支；已验证线索限重复Val2/seed42下的已知RGB局部缺失。

本轮按用户要求制定[实验安排v2](protocols/POST_T_RESEARCH_SEQUENCE_20261011.md)：6项核心F/H/R×8000/16000，共72000更新＋两批48 case的0训练DSM内容诊断，X两项转为不可自动派发储备。H修正为完整编码器后接口（net.rgb＋decoder[:-1]），R加末4编码块；主候选R16不变。v1尚未执行，此次事前修订理由和原文归档均已记录。

顺序：内容前测→H8→F8→R8→R16→H16→F16→内容后测→原件分析。8k后不按成绩筛选长预算组。当前DESIGN_FROZEN_NOT_IMPLEMENTED_NOT_REGISTERED，设计清单不能作执行配置；下一步落实源码、完整配置、参数/梯度与数据流配对、干预复现及控制/上传流程。新训练尚未登记或启动。旧26项不重复运行。

[配对协议v2](protocols/POST_T_PAIRED_ADAPTATION_BUDGET_20261011.md)、[设计清单](../records/post_t_research_plan_v2_20261011/design.json)、[机制结果](experiments/POST_T_MECHANISM_RESULTS_20261011.md)、[完整T](experiments/POST_T_FULL_RESULTS_20261011.md)。T7/U/E原失败门槛保持；不声称双向、独立泛化或排除可训练容量解释。

只GPU0、无SSH、用户执行服务器终端，记录位于/home/jovyan/zzx对应目录；禁Test6/held4/final，不自动重跑/加seed/排DSM镜像。粗排新计划30—60小时未实测，以首个正式worker校准；不能据旧观测写实时状态。

读取顺序：[新对话交接](current/NEW_CHAT_HANDOFF_20261011.md)→[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[PROJECT_STATUS](current/PROJECT_STATUS.md)→[NEXT_EXPERIMENT](current/NEXT_EXPERIMENT.md)→[实验索引](experiments/rebuild_v1/INDEX.md)。
