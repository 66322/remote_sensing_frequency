# 研究决定：六项适应位置×预算配对，补充DSM内容诊断

权威共享源：66322/remote_sensing_frequency，rebuild-v1-protocol-20260915；本地仅工作副本。

最后服务器查询仍为2026-10-11T13:48:26.474610+08:00：旧Post-T队列26/26 COMPLETE、CPU完成、controller及workers退出；0新训练。原件57ef5ad9已离线验收，当前不是新的实时服务器查询。审计范围和限制见[机制结果](../experiments/POST_T_MECHANISM_RESULTS_20261011.md)。

主线保持RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复为旁支。现有实验已验证线索仅限Potsdam fit12→重复Val2 3_11/5_10、seed42、已知RGB局部缺失。DSM_U是保护结果，双向/未知可靠性/独立泛化均未验证。原T7/U/E=False不改，不后验挑T5/M303。

用户本轮要求根据实验结果和论文问题规划安排。现采纳助手提出的v2研究设计：6项核心F/H/R×8000/16000，共72000新优化器调用，固定主候选R16；前后两批DSM内容推理诊断共48 case、0更新。X8/X16为RESERVED_NOT_AUTOMATIC。当前DESIGN_FROZEN_NOT_IMPLEMENTED_NOT_REGISTERED，尚无新执行代码验收、队列、PID或训练启动。

H定义为RGB编码器后的net.rgb投影＋net.decoder[:-1]接口，R加最后4编码块；真正最终分类器net.decoder[-1]冻结。v1遗漏投影且对分类层位置表述不充分，已按实际执行链修正。空间错位不能独立排除容量解释，因此移出核心训练并保留解释边界。本次是新结果产生前的协议修订，v1归档，非修改旧T gate。

固定顺序：内容前测M000_context/M300_context → H8 → F8 → R8 → R16 → H16 → F16 → 内容后测F16/R16 → 上传原件/独立分析。8k后不按成绩筛选16k组。核心R16−F16/R16−H16各≥0.3pp、两tile正，另守R0/保护/六E底线；DSM内容敏感性独立报告。科学负结果不自动重试，技术失败HOLD。

[研究安排与论文问题映射](../protocols/POST_T_RESEARCH_SEQUENCE_20261011.md)；[配对训练细则v2](../protocols/POST_T_PAIRED_ADAPTATION_BUDGET_20261011.md)；[设计清单](../../records/post_t_research_plan_v2_20261011/design.json)；[v1归档](../history/POST_T_PAIRED_ADAPTATION_BUDGET_V1_20261011.md)。

唯一立即动作是落实v2执行包与完整配置、数据随机流、真实梯度名单、干预端点复现和GPU0控制/上传流程，冻结后再由用户在服务器执行。已有26项不重复登记/重跑/重复验收。粗排GPU0约30—60小时未实测，以每类首个正式worker校准；此刻尚未开工，不能给绝对完成时间。

只用GPU0，无SSH；所有服务器记录在/home/jovyan/zzx对应独立目录。禁止Test6/held4/final、不自动重跑失败配方或增加种子。不自动排DSM镜像、新频域模块或恢复旁支。双向性下一步须有真实反向有效支持与简单参考，不能把DSM_U保护当成双向增益。后续独立来源/多seed只规划不擅自执行。
