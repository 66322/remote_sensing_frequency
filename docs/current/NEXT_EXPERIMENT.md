# 下一步：修复已确认的A0 IPC阻塞，再显式接续（2026-10-30）

最新实际状态：原A0双子进程已启动，但均报`AF_UNIX path too long`，用户确认PID2426676/2426731/2426732仍活着，未列出progress/完成/端点。当前是IPC工程阻塞，不是科学阴性；不重跑原入口。按[独立修复说明](../experiments/POST_M2_A0_IPC_REPAIR_20261030.md)保留旧记录、核对并停止本次故障进程、验证一次CPU IPC，再显式接续新修复目录。没有正式成功更新回执，不能由缺失文件宣称精确零更新。

历史启动回执：用户已派发原A0后台入口，PID `2426676`，日志文件名时间戳`20261030T171015`，见[回执](../../records/post_m2_a0_capability_20261029/continuation_dispatch_user_receipt_20261030.json)。目前只证明后台入口派发，预检通过、GPU子进程、正式首更和阶段完成仍未回传。此派发记录已被后续AF_UNIX故障观测更新；当前按上方独立修复流程执行。

用户已要求按[最新主计划](../experiments/POST_M2_MULTIROUTE_PLAN_20261030.md)安排实验；[首批执行r1](../experiments/POST_M2_MULTIROUTE_EXECUTION_20261030.md)和[机器清单](../../records/post_m2_multiroute_v2_20261030_release/execution_plan.json)已完成实现及本地检查，无目标训练回执。

尚未部署的新任务使用轻量测速修订，精确代码提交见[当前发布回执](../../records/post_m2_multiroute_v2_20261030_release/publication_receipt.json)。若已安装/启动历史4fbabd6版本则读其既有状态，不热改或重启。

当前A0接续：旧入口已因长TMPDIR报IPC错误，进程仍在，不能再用原启动命令。新修复工具先核对归属、保存证据并停止本次故障树；原进度/端点若存在即停止重放；否则验证一次CPU进程张量通信并复用两份profile。prepare不训练，随后由用户显式start新目录，按原合同各2k/seed42→校准→screen→条件外层；无自动重试。

后续Full独立入口（当前不另派发）：服务器沿既有remote_sensing，按本次固定发布commit运行bootstrap --start。它只下载小型固定代码载荷，后台pipeline自动完成CPU数据/公共权重检查、七条真实路径profile、合格后11个Full作业/88k；不另等人工放行、不在训练中安装或下载。

排程：B0/B1合格后按就绪任务填满两卡，优先Q1→Q2→Q3真实数据依赖并穿插S/G；G2/G3可在G1合格后并行，S2/S3可在S1合格后并行。固定每卡一个常驻进程，复用编码器与训练图块；新头、优化器、样本流独立绑定。源/包/数据/环境不变的既有检查复用。

按用户要求，每真实新路径仅一个配置，预热1步、计时3步，共4个丢弃更新；七路径最多28，两个新空间头合计最多8。Full复用已有DINOv2的4worker/micro16；空间头复用各自原骨干配置；不再扫worker/microbatch。有效batch16不变，短计时仅作粗估，正式训练中原有日志继续记录真实耗时。单配置仍由数据等待主导则停，正式训练/评价超过自己profile2.5倍亦停诊断。profile后写measured_budget.json，不引用A0速度外推。原始错误栈保存、共性首败停派发，无自动重试或热改。

A分支独立：原A0代码c22a046不变；2026-10-30 16:30:50已收到[DINOv3源码/真实加载/profile通过回执](../../records/post_m2_a0_capability_20261029/dino3_readiness_server_receipt_20261030.json)，DINOv2检查复用，不重复下载/哈希/测速。下一步直接按原pair合同正式训练，薄层入口仅串接已授权阶段；新增两空间头共4k在原A0完成且两卡空闲时独立运行。整个A0/A空间4探针共8k，与Full队列合计96k。DINOv3未就绪不阻塞G/Q/S，Full/NB128结果分开解释。

阶段完整配对后复盘G/Q/S主指标、保护约束和错配/时序控制；科学阴性只收缩对应机制，INVALID不当科学失败。C/P/E/F和频率子实验仍有各自前置，不自动扩队列/种子。M2清理仍暂缓；旧队列不重启，封存集不开。

本次新增A0后台入口派发回执，尚无正式首更、阶段完成或新Full流水线启动回执；不得据此重复启动既有队列。新入口将后续Torch/CUDA临时缓存放在ROOT内，通过链接复用已验权重，不删除原/root缓存副本。
