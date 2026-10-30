# 当前交接：多路线 v2 首批执行版本 r1（2026-10-30）

最新Full实际进度19:38:20：[回执](../../records/post_m2_multiroute_v2_20261030_r1/progress_observations/20261030T193820/observation.json)确认已通过CPU准备和七路径轻量profile并进入正式训练。GPU0/PID2518876：Q2第3000步，最近100步2.238秒、取数等待0.149ms；GPU1/PID2518877：G1第1100步，100步2.954秒、等待0.159ms。两窗口取数等待占平均步时均<1%。B0/B1/Q1/S1已返回8k训练循环，至少36,100次Full优化更新为源码/调度推断下界；S1是否资格通过及各方法分数仍待现成结果JSON。当前保持运行，只读已有结果与heartbeat，不重启、不改包、不加测速。

2026-10-30用户进一步修订：加载/测速仅做轻量验证，已有通过项直接复用；新路径只保留一个已有依据的配置，1步预热+3步计时，计时仅作粗估，不跑多组扫参或额外百步训练。七条Full路径最多28个丢弃更新，两个空间头合计最多8；正式科学实验训练预算与测速分开，不能把各2k正式A0误当测速。仅适用于尚未部署的新快照，已安装/运行不热改、不重启，原A0 c22及已测回执不变。

权威分支rebuild-v1-protocol-20260915。[研究主计划](../experiments/POST_M2_MULTIROUTE_PLAN_20261030.md)、[执行合同](../experiments/POST_M2_MULTIROUTE_EXECUTION_20261030.md)、[机器清单](../../records/post_m2_multiroute_v2_20261030_release/execution_plan.json)。本轮用户明确要求按最新规划安排并优化资源；已完成实现、本地14项检查和独立载荷核验；尚无目标Linux/真实新路径profile/正式更新回执。

未部署新任务采用本次轻量测速修订，精确代码提交和命令见[当前发布回执](../../records/post_m2_multiroute_v2_20261030_release/publication_receipt.json)；历史4fbabd6b135a41c1ba0891120dcac6546880bf47快照保留。已有安装/启动回执时先读状态，不为缩短准备检查替换或重启已有执行。

## 当前接续

A0原两线性头已在[独立IPC修复run](../experiments/POST_M2_A0_IPC_REPAIR_20261030.md)完成各2k与校准/外层评价。原profile复用，准备优化更新0；失败旧attempt仍保留，精确未记录更新数未知。14份现成小JSON已收齐并核对，外层为负向比较，不重算A0。独立Full队列已派发PID2517098，现在只读原日志/heartbeat确认实际进度。修复后的新入口按同一科学合同串接各2k训练、校准、screen与条件外层评价，不重做检查；旧入口保留停态。既有Full队列若已运行（包括CPU准备）则不派发第二控制器。Full独立入口继续是在既有remote_sensing环境按固定发布commit执行bootstrap --start；缺少启动回执时不能重复启动。服务器由用户操作，无SSH。小载荷保存于ROOT/execution/post_m2_multiroute_v2_20261030_r1；运行目录ROOT/records/post_m2_multiroute_v2_20261030_r1；ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro。后台pipeline依次CPU数据/真实公共权重严格加载→七条真实路径profile→全部合格后11作业/88k，阶段间自动接续，无隐藏下载/安装或人工确认等待。

每卡常驻一个进程，跨作业复用DINOv2与六拟合tile；头/优化器独立初始化。G/S候选及错配控制在各自主控制合格后可并行；Q3必须读取Q2实际暴露记录。默认42，有效batch16，Full512监督。G/Q/S不等DINOv3。真实耗时由measured_budget.json给出，A0速度不外推。共性首败停止整队、保留原栈，仅终止自身进程组，不自动重试/改配方/删锁。

## A分支与证据边界

原A0脚本逐字节保持c22a046407daf42064cbb161429f2648c9b86d66，DINOv2检查复用；DINOv3下载/首次SHA256后，源码HEAD、真实加载和profile也通过，见[最新回执](../../records/post_m2_a0_capability_20261029/dino3_readiness_server_receipt_20261030.json)及[原profile字段](../../records/post_m2_a0_capability_20261029/profile_dino3.json)。原两线性头成功完成回执为各2k，终端确认4k及完整评价阶段；原始outer JSON已归档，pooled fg5为DINOv2 71.0394%、DINOv3 70.3867%。新增薄层入口只串接原阶段，不修改原科学合同或阈值；首败停止、无自动重试。原环境最后已确认Python3.11.13/Torch2.7.1+cu126、torchvision0.22.1/torchaudio2.7.1、pip check通过，不重建。

新A空间头代码已交付，两骨干同19,254参数、同原A0样本流/NB128监督，各2k；依原A0双模型真实检查和正式训练完成，在双卡空闲窗口独立分阶段运行，不混入Full队列。原A0各2k+空间各2k合计8k；与11×8k共96k。旧线性头2,310参数，不能宣称线性/空间同容量，也不能绕过旧外层screen。

## 最后实际服务器状态

历史原A0测速观测为2026-10-30 16:30:50.996411+08:00 DINOv3 profile完成；此后19:01已完成实际训练与评价：8worker/micro16，中位14.36ms/步，取数等待0.109ms；评价batch16，529窗口预测/拼接0.6641秒（不含数据加载/完整指标统计）。首次数据加载35.19秒、总profile43.74秒、160丢弃更新；不算正式训练。GPU1在该检查前通过占用保护，当前GPU子进程占用待新修复日志，不能把18:59后台派发当成正式训练已进行。此前inventory确认F0 12tile、CPU192、约2.04TB RAM、GPU0/1各81081MiB空闲，是历史观测。新启动由目标检查确认实际空闲，不动2–7卡。

M2已完成108训练/3,456,000更新/77,868评价，DF配方关闭；J工程停止，无科学结果。首清理删除90保留18；最终清理19:15在预删除统计空值相减失败，未删除，仍按用户要求暂缓。授权不撤回，本轮不恢复清理、不为新研究强留旧专家。

## 回传和接续

小证据自动导出压缩evidence.jsonl.gz，含逐tile整数矩阵、边界/ROI计数、训练轨迹、真实暴露/重放、来源、成本和原始错误日志。先释放GPU再沿已有认证上传records/运行名；认证不可用保留UPLOAD_PENDING，后续仅publish不重算。原始数据/公共权重不进普通Git，最少端点保留服务器。

Full流水线的本地Windows/Python3.9.25/Torch2.8.0+cpu检查不能替代其目标Linux/fork/CUDA/真实权重与吞吐验收。A0两骨干目标加载/测速已通过，与Full验收分开。已收到A0正向内校准开发结果和阶段完成回执，外层小JSON已归档并经计数核对；Full CPU准备与七路径profile已放行，实际Q2/G1更新回执已收到；完整作业结果/科学比较尚待小JSON。科学主线未更换，封存集未打开，C/P/E/F仍按自身条件准备。
