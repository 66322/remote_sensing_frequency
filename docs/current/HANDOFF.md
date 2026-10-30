# 当前交接：多路线 v2 首批执行版本 r1（2026-10-30）

权威分支rebuild-v1-protocol-20260915。[研究主计划](../experiments/POST_M2_MULTIROUTE_PLAN_20261030.md)、[执行合同](../experiments/POST_M2_MULTIROUTE_EXECUTION_20261030.md)、[机器清单](../../records/post_m2_multiroute_v2_20261030_release/execution_plan.json)。本轮用户明确要求按最新规划安排并优化资源；已完成实现、本地14项检查和独立载荷核验；尚无目标Linux/真实新路径profile/正式更新回执。

## 唯一下一步

在既有remote_sensing环境按固定发布commit执行bootstrap --start。服务器由用户操作，无SSH。小载荷保存于ROOT/execution/post_m2_multiroute_v2_20261030_r1；运行目录ROOT/records/post_m2_multiroute_v2_20261030_r1；ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro。后台pipeline依次CPU数据/真实公共权重严格加载→七条真实路径profile→全部合格后11作业/88k，阶段间自动接续，无隐藏下载/安装或人工确认等待。

每卡常驻一个进程，跨作业复用DINOv2与六拟合tile；头/优化器独立初始化。G/S候选及错配控制在各自主控制合格后可并行；Q3必须读取Q2实际暴露记录。默认42，有效batch16，Full512监督。G/Q/S不等DINOv3。真实耗时由measured_budget.json给出，A0速度不外推。共性首败停止整队、保留原栈，仅终止自身进程组，不自动重试/改配方/删锁。

## A分支与证据边界

原A0脚本逐字节保持c22a046407daf42064cbb161429f2648c9b86d66，DINOv2检查复用；DINOv3原生pth来源/下载/加载/profile回执仍缺，原双模型线性头正式训练回执0。原环境最后已确认Python3.11.13/Torch2.7.1+cu126、torchvision0.22.1/torchaudio2.7.1、pip check通过，不重建。

新A空间头代码已交付，两骨干同19,254参数、同原A0样本流/NB128监督，各2k；依原A0双模型真实检查和正式训练完成，在双卡空闲窗口独立分阶段运行，不混入Full队列。原A0各2k+空间各2k合计8k；与11×8k共96k。旧线性头2,310参数，不能宣称线性/空间同容量，也不能绕过旧外层screen。

## 最后实际服务器状态

仍为2026-10-29 20:18:55 DINOv2 profile。此前inventory确认F0 12tile、CPU192、约2.04TB RAM、GPU0/1各81081MiB空闲，是历史观测。新启动由目标检查确认实际空闲，不动2–7卡。

M2已完成108训练/3,456,000更新/77,868评价，DF配方关闭；J工程停止，无科学结果。首清理删除90保留18；最终清理19:15在预删除统计空值相减失败，未删除，仍按用户要求暂缓。授权不撤回，本轮不恢复清理、不为新研究强留旧专家。

## 回传和接续

小证据自动导出压缩evidence.jsonl.gz，含逐tile整数矩阵、边界/ROI计数、训练轨迹、真实暴露/重放、来源、成本和原始错误日志。先释放GPU再沿已有认证上传records/运行名；认证不可用保留UPLOAD_PENDING，后续仅publish不重算。原始数据/公共权重不进普通Git，最少端点保留服务器。

本地Windows/Python3.9.25/Torch2.8.0+cpu检查不能替代目标Linux/fork/CUDA/真实权重与吞吐验收。不存在新科学结果；文档同步不等于控制器部署。科学主线未更换，封存集未打开，C/P/E/F仍按自身条件准备。
