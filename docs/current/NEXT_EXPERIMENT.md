# 下一步：部署多路线 v2 r1，按真实测速自动放行（2026-10-30）

用户已要求按[最新主计划](../experiments/POST_M2_MULTIROUTE_PLAN_20261030.md)安排实验；[首批执行r1](../experiments/POST_M2_MULTIROUTE_EXECUTION_20261030.md)和[机器清单](../../records/post_m2_multiroute_v2_20261030_release/execution_plan.json)已完成实现及本地检查，无目标训练回执。

固定代码提交`4fbabd6b135a41c1ba0891120dcac6546880bf47`；见[完整启动命令与发布回执](../../records/post_m2_multiroute_v2_20261030_release/publication_receipt.json)。

唯一下一步：服务器沿既有remote_sensing，按本次固定发布commit运行bootstrap --start。它只下载小型固定代码载荷，后台pipeline自动完成CPU数据/公共权重检查、七条真实路径profile、合格后11个Full作业/88k；不另等人工放行、不在训练中安装或下载。

排程：B0/B1合格后按就绪任务填满两卡，优先Q1→Q2→Q3真实数据依赖并穿插S/G；G2/G3可在G1合格后并行，S2/S3可在S1合格后并行。固定每卡一个常驻进程，复用编码器与训练图块；新头、优化器、样本流独立绑定。源/包/数据/环境不变的既有检查复用。

每真实路径最多120丢弃更新、共七路径最多840；0/4/8worker及micro16/8比较保持有效batch16。最快配置仍由数据等待主导则停，正式训练/评价超过自己profile2.5倍亦停诊断。profile后写measured_budget.json，不引用A0速度外推。原始错误栈保存、共性首败停派发，无自动重试或热改。

A分支独立：原A0代码c22a046不变，只补DINOv3缺项后按原pair合同；新增两空间头共4k在原A0完成且两卡空闲时独立运行。整个A0/A空间4探针共8k，与Full队列合计96k。DINOv3未就绪不阻塞G/Q/S，Full/NB128结果分开解释。

阶段完整配对后复盘G/Q/S主指标、保护约束和错配/时序控制；科学阴性只收缩对应机制，INVALID不当科学失败。C/P/E/F和频率子实验仍有各自前置，不自动扩队列/种子。M2清理仍暂缓；旧队列不重启，封存集不开。
