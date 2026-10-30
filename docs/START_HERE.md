# 共享入口：多路线 v2 首批执行交付（2026-10-30）

已接收A0全部14份现成小JSON，16个整数矩阵与指标核对一致，见[结果与阶段复盘](experiments/POST_M2_A0_RESULTS_AND_REVIEW_20261030.md)：内校准DINOv3−DINOv2 +1.6257pp，外层开发−0.6527pp（71.0394%→70.3867%），四tile两升两降。原内校准screen保留READY；整体优势未在外层复现，A1/A2保持条件且未入队，独立空间读出及G/Q/S不关闭。Full固定载荷已安装、后台入口PID2517098已派发；正式进度尚未回传。当前只读现有pipeline.log和heartbeat_gpu0/1，不重新启动、测速或改配方。

2026-10-30用户进一步修订：加载/测速仅做轻量验证，已有通过项直接复用；新路径只保留一个已有依据的配置，1步预热+3步计时，计时仅作粗估，不跑多组扫参或额外百步训练。七条Full路径最多28个丢弃更新，两个空间头合计最多8；正式科学实验训练预算与测速分开，不能把各2k正式A0误当测速。仅适用于尚未部署的新快照，已安装/运行不热改、不重启，原A0 c22及已测回执不变。

先读[研究决定](current/RESEARCH_DECISION.md)、[交接](current/HANDOFF.md)、[状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)。长期规则见[AGENTS](../AGENTS.md)、[执行约定](protocols/EXECUTION_CONTRACT.md)和[实验规划规则](protocols/EXPERIMENT_PLANNING_RULES.md)。

本轮用户要求按最新规划安排实验，避免M2式代码与资源等待。已实现[执行交付 r1](experiments/POST_M2_MULTIROUTE_EXECUTION_20261030.md)、[机器执行清单](../records/post_m2_multiroute_v2_20261030_release/execution_plan.json)、[小型固定载荷](../records/post_m2_multiroute_v2_20261030_release/payload_manifest.json)。本地14项检查及独立包核验见[本地验收](../records/post_m2_multiroute_v2_20261030_release/local_checks.json)。目标Linux/CUDA、真实新路径吞吐、正式训练均待服务器回执，不写已排队。

研究依据继续用[多路线主计划](experiments/POST_M2_MULTIROUTE_PLAN_20261030.md)与[文献矩阵](experiments/POST_M2_MULTIROUTE_LITERATURE_20261030.md)。G/Q/S基于现有DINOv2，不等A0阳性。首批15作业/96k，其中主流水线B0/B1+G/Q/S为11作业/88k；原A0与新空间读出各4k独立。C/P/E/F及频率子实验仍有条件，不自动启动。

服务器用户执行，无SSH；物理GPU0/1，各一卡一常驻进程。载荷下载后后台依次CPU真实权重/数据检查→每真实路径测速→全部合格后正式队列；不在训练中下载/安装，首败停派发、不自动重试。GPU先释放再上传压缩小证据。

A0继续固定c22a046407daf42064cbb161429f2648c9b86d66；DINOv2既有检查复用。2026-10-30 16:30:50已收到[DINOv3源码HEAD、真实加载与profile通过回执](../records/post_m2_a0_capability_20261029/dino3_readiness_server_receipt_20261030.json)；原A0各2k及校准/外层阶段已完成，外层原始分数已收齐，DINOv3总体低0.6527pp。原小型入口已发生IPC故障，当前采用[独立修复入口](experiments/POST_M2_A0_IPC_REPAIR_20261030.md)在停止已确认故障进程、验证IPC后接续原pair训练→校准→screen→条件外层开发评价，不重复下载/哈希/测速。GPU0/1若正被占用或Full控制器正准备/运行，则不派发竞争队列。该A0回执不替代Full新路径验收。

M2验收与配方关闭、J工程停止保持；M2最终清理因预删除空值统计首败仍暂缓，最后确认18端点，不写0，不自动恢复。GitHub分支rebuild-v1-protocol-20260915为跨电脑权威。
