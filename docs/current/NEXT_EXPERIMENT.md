# 下一步：读取修复版A0正式进度，不重复启动（2026-10-30）

2026-10-30 18:59:13（北京时间）已收到[修复准备通过](../../records/post_m2_a0_ipcfix_20261030/repair_ready.json)与[新后台入口派发](../../records/post_m2_a0_ipcfix_20261030/repair_dispatch.json)回执：PID2506856，短TMPDIR=/home/jovyan/zzx/tmp/a0_ipc，原profile复用、准备优化更新0。成功prepare报告已完成旧归属进程停止与一次CPU IPC检查，详细停止/IPC原件仍在服务器。当前唯一下一步是读取新run的repair_continuation.log和pair_train_dino2/dino3.log确认正式首更/完成或原始错误，不再prepare/start，不再测速；尚未收到正式成功更新回执。

用户已要求按[最新主计划](../experiments/POST_M2_MULTIROUTE_PLAN_20261030.md)安排实验；[首批执行r1](../experiments/POST_M2_MULTIROUTE_EXECUTION_20261030.md)和[机器清单](../../records/post_m2_multiroute_v2_20261030_release/execution_plan.json)已完成实现及本地检查，无目标训练回执。

尚未部署的新任务使用轻量测速修订，精确代码提交见[当前发布回执](../../records/post_m2_multiroute_v2_20261030_release/publication_receipt.json)。若已安装/启动历史4fbabd6版本则读其既有状态，不热改或重启。

当前A0接续：新prepare已通过，用户已显式start并得到PID2506856；当前只读新父/子日志确认首更、阶段完成或错误。新run为ROOT/records/post_m2_a0_ipcfix_20261030，原记录保留；入口按原科学合同各2k/seed42→校准→screen→条件外层，无自动重试。不要重复prepare/start，不另开加载/测速或竞争队列。

后续Full独立入口（当前不另派发）：服务器沿既有remote_sensing，按本次固定发布commit运行bootstrap --start。它只下载小型固定代码载荷，后台pipeline自动完成CPU数据/公共权重检查、七条真实路径profile、合格后11个Full作业/88k；不另等人工放行、不在训练中安装或下载。

排程：B0/B1合格后按就绪任务填满两卡，优先Q1→Q2→Q3真实数据依赖并穿插S/G；G2/G3可在G1合格后并行，S2/S3可在S1合格后并行。固定每卡一个常驻进程，复用编码器与训练图块；新头、优化器、样本流独立绑定。源/包/数据/环境不变的既有检查复用。

按用户要求，每真实新路径仅一个配置，预热1步、计时3步，共4个丢弃更新；七路径最多28，两个新空间头合计最多8。Full复用已有DINOv2的4worker/micro16；空间头复用各自原骨干配置；不再扫worker/microbatch。有效batch16不变，短计时仅作粗估，正式训练中原有日志继续记录真实耗时。单配置仍由数据等待主导则停，正式训练/评价超过自己profile2.5倍亦停诊断。profile后写measured_budget.json，不引用A0速度外推。原始错误栈保存、共性首败停派发，无自动重试或热改。

A分支独立：原A0代码c22a046不变；2026-10-30 16:30:50已收到[DINOv3源码/真实加载/profile通过回执](../../records/post_m2_a0_capability_20261029/dino3_readiness_server_receipt_20261030.json)，DINOv2检查复用，不重复下载/哈希/测速。下一步直接按原pair合同正式训练，薄层入口仅串接已授权阶段；新增两空间头共4k在原A0完成且两卡空闲时独立运行。整个A0/A空间4探针共8k，与Full队列合计96k。DINOv3未就绪不阻塞G/Q/S，Full/NB128结果分开解释。

阶段完整配对后复盘G/Q/S主指标、保护约束和错配/时序控制；科学阴性只收缩对应机制，INVALID不当科学失败。C/P/E/F和频率子实验仍有各自前置，不自动扩队列/种子。M2清理仍暂缓；旧队列不重启，封存集不开。

本次新增A0后台入口派发回执，尚无正式首更、阶段完成或新Full流水线启动回执；不得据此重复启动既有队列。新入口将后续Torch/CUDA临时缓存放在ROOT内，通过链接复用已验权重，不删除原/root缓存副本。
