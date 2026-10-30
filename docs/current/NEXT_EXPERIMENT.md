# 下一步：跟进已派发Full队列，A0完整结果已归档（2026-10-30）

已接收A0全部14份现成小JSON，16个整数矩阵与指标核对一致，见[结果与阶段复盘](../experiments/POST_M2_A0_RESULTS_AND_REVIEW_20261030.md)：内校准DINOv3−DINOv2 +1.6257pp，外层开发−0.6527pp（71.0394%→70.3867%），四tile两升两降。原内校准screen保留READY；整体优势未在外层复现，A1/A2保持条件且未入队，独立空间读出及G/Q/S不关闭。Full固定载荷已安装、后台入口PID2517098已派发；正式进度尚未回传。当前只读现有pipeline.log和heartbeat_gpu0/1，不重新启动、测速或改配方。

用户已要求按[最新主计划](../experiments/POST_M2_MULTIROUTE_PLAN_20261030.md)安排实验；[首批执行r1](../experiments/POST_M2_MULTIROUTE_EXECUTION_20261030.md)和[机器清单](../../records/post_m2_multiroute_v2_20261030_release/execution_plan.json)已完成实现及本地检查，Full无目标训练回执，原A0已有4k成功完成证据。

尚未部署的新任务使用轻量测速修订，精确代码提交见[当前发布回执](../../records/post_m2_multiroute_v2_20261030_release/publication_receipt.json)。若已安装/启动历史4fbabd6版本则读其既有状态，不热改或重启。

当前A0已完整归档：新run为ROOT/records/post_m2_a0_ipcfix_20261030，各2k/seed42及全部阶段完成，14份小JSON和逐tile整数计数均已收到。内校准+1.6257pp、外层−0.6527pp。原screen保留READY，无新增外层数值门槛；研究复盘建议A1/A2不因内筛阳性自动追加，空间读出仍按原预算独立候选。不要重跑A0或为补文档重新推理。

Full入口已由用户安装并派发（PID2517098、代码d15f34e8），当前不要再执行bootstrap --start。仅读ROOT/records/post_m2_multiroute_v2_20261030_r1/pipeline.log与heartbeat_gpu0/1.json，区分CPU准备、profile、正式更新、完成或原始错误。它只下载小型固定代码载荷，后台pipeline自动完成CPU数据/公共权重检查、七条真实路径profile、合格后11个Full作业/88k；不另等人工放行、不在训练中安装或下载。

排程：B0/B1合格后按就绪任务填满两卡，优先Q1→Q2→Q3真实数据依赖并穿插S/G；G2/G3可在G1合格后并行，S2/S3可在S1合格后并行。固定每卡一个常驻进程，复用编码器与训练图块；新头、优化器、样本流独立绑定。源/包/数据/环境不变的既有检查复用。

按用户要求，每真实新路径仅一个配置，预热1步、计时3步，共4个丢弃更新；七路径最多28，两个新空间头合计最多8。Full复用已有DINOv2的4worker/micro16；空间头复用各自原骨干配置；不再扫worker/microbatch。有效batch16不变，短计时仅作粗估，正式训练中原有日志继续记录真实耗时。单配置仍由数据等待主导则停，正式训练/评价超过自己profile2.5倍亦停诊断。profile后写measured_budget.json，不引用A0速度外推。原始错误栈保存、共性首败停派发，无自动重试或热改。

A分支独立：原A0代码c22a046不变；2026-10-30 16:30:50已收到[DINOv3源码/真实加载/profile通过回执](../../records/post_m2_a0_capability_20261029/dino3_readiness_server_receipt_20261030.json)，DINOv2检查复用，不重复下载/哈希/测速。原pair正式训练、校准和外层评价已完成，不再运行；新增两空间头共4k在原A0完成且两卡空闲时独立运行。整个A0/A空间4探针共8k，与Full队列合计96k。DINOv3未就绪不阻塞G/Q/S，Full/NB128结果分开解释。

阶段完整配对后复盘G/Q/S主指标、保护约束和错配/时序控制；科学阴性只收缩对应机制，INVALID不当科学失败。C/P/E/F和频率子实验仍有各自前置，不自动扩队列/种子。M2清理仍暂缓；旧队列不重启，封存集不开。

本次已收到A0训练/校准/外层完成回执；Full已收到安装和入口派发回执，尚未收到CPU/profile/正式更新。先前首次启动命令已完成，不再运行；现在只读状态和原日志。新入口将后续Torch/CUDA临时缓存放在ROOT内，通过链接复用已验权重，不删除原/root缓存副本。
