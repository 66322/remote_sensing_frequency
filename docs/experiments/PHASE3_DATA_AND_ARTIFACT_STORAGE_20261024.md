# 当前队列输入数据、产物路径与保留规则（2026-10-24）

本记录解释用户关于新数据、实验产生文件及保留内容的疑问。按7823f33分支头及其执行源码核对；无新服务器查询，最后服务器观测仍为2026-10-24 09:54:39+08:00。下面区分代码已实现的保存规则与现场已生成文件：M2仅确认两条教师更新2600/2620，尚无完成端点；后段尚未运行。不能把未来产物清单写成文件已经齐全。

## 新输入只属于T/V

M2、J、R用现有Potsdam Fit12的RGB、DSM、语义标签，不需要额外下载新数据。源码配置configs/rebuild_v1/r05_quality_plus_dropout_16k.json指向/home/jovyan/zzx/projects_zys/raw_extract/Potsdam_unzipped；当前实际文件位置、大小、SHA、形状与归一化以M2的input_index.json冻结记录为准，本次未现场检查数据目录。

T为3DCD双时相高度变化，V为P³建筑对象实验，是用户此前明确“连新数据方向也规划入队”后加入。它们分别需要真实双时相观测/变化标签和RGB/点云/建筑实例标签。现有Fit12语义标签不能提供这两个任务的真实监督，M2生成的预测或统计也不能替代新任务真值。不是M2启动后临时增加的数据要求，不是原数据丢失。

新数据原始文件的实际下载目录尚未收到验收证据，不能编造为已存在。各源文件绝对路径必须在/home/jovyan/zzx内，经catalog登记；建议源catalog路径为/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/phase3_combined_public_catalog.json，它只是索引，不是数据本体。程序不自动下载；两数据集均通过合同后，合并目录冻结catalog.json，才进入T/V。未就绪不影响M2/J/R执行，到该依赖点WAIT_PUBLIC_DATA，不自动跳过或另起训练。

## 当前产物根目录

M2（记作M2）：
/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m2_revision_20261024T092814_2738345

J/R/T/V共用合并目录（记作Q）：
/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_combined_revision_20261024T092814_2738345

两者均为服务器路径，不是本地Windows副本。旧失败run、当前repairs内工程前史保留，与这两处当前产物区分。并不为每个后续阶段再创建一套根目录。

## 保留什么

| 内容 | 当前代码位置与含义 |
|---|---|
| M2最终模型 | M2/jobs/<jobID>/endpoint.pth；每个成功作业32000步最终端点，complete.json绑定checkpoint SHA/初始化/实际样本流/GPU等 |
| 后段最终模型 | Q/jobs/J_...、R_...、T_...、V_.../endpoint.pth；J为条件头，依赖M2绑定专家；R存RGB/DSM/头，T/V存对应模型 |
| 配置与复现绑定 | M2和Q的plan.json、registration.json、源码清单/快照；M2的folds.json、input_index.json、pretrained.json、resource_profile.json；修订runtime及namespace回执；T/V冻结catalog.json和逐作业来源SHA |
| 训练过程 | jobs/<jobID>/parameters.json、trajectory.jsonl、batch_hashes.jsonl、progress.json、complete.json；后段另有training_complete.json（J/R），age_*.json阶段回执等，具体按各阶段实现 |
| M2逐案例充分统计 | M2/case_counts.jsonl.gz、all_aggregates.jsonl.gz；保留逐tile/逐mask/条件/模型换配的整数混淆矩阵与联合计数，包含救回/损伤、概率融合曲线、margin和校准统计等，可离线重算既定指标 |
| M2年龄评价 | M2/trajectory_counts/<jobID>/<step>_<tile>.json；8k/16k/24k/32k的外层评价计数。不是保留四份年龄模型权重或四份完整预测图 |
| 后段评价 | Q/jobs/<jobID>/metrics.json；J/R逐tile/条件整数6×6矩阵；T为变化2×2矩阵及已变化区高度绝对误差和计数；V为建筑像素2×2矩阵、对象TP/FP/FN/并合拆分和边界计数 |
| 汇总报告 | M2/publication/下REPORT.md、summary.json、gates.json、metrics.csv、F0/F1/F2_counts.jsonl.gz、server_evidence_index.json、manifest.json；Q/publication/J、R、T、V内各自summary/metrics等，J另有REPORT.md、gates.json、evidence_index.json |
| 运行与失败材料 | 两根目录queue_status.json、nohup.log、各阶段status、failures/skipped、检查及repairs/回执等；负结果和失败证据保留，不因失败清目录 |

参数、模型和记录须作为完整绑定使用：例如J的头文件不能脱离其M2源专家端点解释。原始数据仍保留原位置，不在每个job目录复制一遍。

## 内存中间量与有限回收

训练裁剪/增强图、teacher在线概率、特征、整tile logits/概率、退化mask的展开数组、CPU计数输入按既定内存生命周期消费；M2使用匿名memfd共享，最后引用关闭后回收，完整数组不经pickle整块复制、不建立整轮磁盘logit缓存。M2保留紧凑mask_design图元/种子、配置和原始计数，而不是每个增强或mask都存一张大图。P³/3DCD适配器TileCache每worker上限3GiB，用完clear，不产生持久crop缓存。预训练、CUDA编译缓存等工程缓存与整轮派生数组缓存不是一回事，不宣称run内完全没有cache/temporary文件。

M2每1000更新覆盖一个last_resume.pth（含optimizer/RNG），不是每1000步永久增加一个checkpoint。只有32k成功端点和四年龄×四tile共16份轨迹计数全部确认后，才按白名单删除该作业rolling恢复文件，保留retirement/<jobID>.json。最终endpoint.pth、必要计数与日志保留；失败状态不因这一成功退役规则删除。J/R/T/V当前没有相同的滚动optimizer恢复文件承诺，不能笼统说各段都有断点恢复。

J/R/T/V的age_*.json目前是训练年龄/样本流或时间回执，不等同M2四年龄全tile性能评价，也不是中间权重。训练日志能够画loss/速度曲线，但不能据age标记宣称存在每个中间点的性能曲线。

当前执行链不默认导出全量预测PNG/TIFF、每像素概率/特征或建筑实例栅格。因此保存的计数足够重算已登记指标，但不能从计数反推出任意像素图或新增空间统计。若后续论文需端点可视化，可用保留原始输入、最终模型与绑定配置另做规定范围的推理，不需要重训；没有保存的中间年龄模型不能据此承诺任意年龄图可恢复。本次未增加导图或推理作业。

## GitHub与服务器不等价

GitHub保存协议/代码/共享状态/用户回执及按清单上传的轻量结果，不保存原始数据集、全量权重或大型像素数组。M2上传器在finalize后尝试上传M2/publication轻量清单到仓库records/<M2目录名>/；仅用现有凭据，没有凭据则留upload_pending.json，计算结果仍在服务器，不要求重训。

当前control_phase3_combined及J/R/T/V运行器没有完整统一自动上传流程；它们生成服务器publication并不意味着已经出现在GitHub。额外752d/25b修订材料也不保证被原M2上传器打包。结束须按显式轻量清单整理同步并回读，确认各段端点/计数/轨迹及额外修订回执。源码实现与当前GitHub“已接收原件”必须分别报告。本记录仅补充说明，不改变运行、保存或删除策略。