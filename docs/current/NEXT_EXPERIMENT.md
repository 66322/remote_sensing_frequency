# 下一实验：Phase2已登记，待查询准备与smoke阶段（2026-10-13）

## 最新登记回执（用户提供）

用户终端回执：2026-10-13 14:59（Asia/Shanghai，来自目录及日志时间；不是后续status查询）。代码固定 f01f9e94f1e9bdcc9c126b5bc3ffb2a7d3b492f5；PHASE2_REGISTERED，controller PID 1304554，GPU0/1。目录：`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase2_matched_20261013T145903_1304150`；日志：`nohup_20261013T145909801545.log`。核心4训练48k、最多6训练64k、无24h截止。

已完成登记，但尚无准备/双卡smoke/正式训练的status原件，不能据此声称这些阶段已通过或正在训练。下一步只读执行此目录的code/scripts/status_phase2.py并查看上述nohup日志；勿再次enqueue。记录：[登记原件](../../records/phase2_registration_20261013/receipt.txt)。激活remote_sensing不改变启动脚本显式使用d18_dino Python。没有新指标、Test6访问或失败配方重跑。

用户2026-10-13已明确“按照上述规划进行具体实验吧”。Phase2执行包现已实现，已收到服务器登记回执；准备与GPU smoke尚待status查询，无新训练结果。核心A_RGB/A_DSM各16k、B0/B2各8k（4训练48k）；C/L、静态后剩余差距及保护通过后自动派B1/B3各8k（最多6训练64k）。GPU0/1、无24h截止、失败HOLD且不自动重试/增seed。

[执行协议](../protocols/PHASE_2_EXECUTION_20261013.md)、[完整科学设计](../protocols/PHASE_2_MATCHED_COMPLEMENTARITY_20261013.md)、[技术验收](../../records/phase2_implementation_20261013/verification.json)。10项CPU检查/13个Python语法检查通过，旧160D/720身份/120dose计数重用另核验；真实DINO/Torch2.2.2+cu121/两卡数值与实际batch16烟雾检查由服务器完成，之前不派正式训练。down4明确沿既有bilinear+antialias算子，修正原设计“area”措辞；门禁使用与head输入一致的窗口熵差重建，空健康支持记NA。

资源已落实：只读resident/mmap输入、每卡crop8/prefetch8、head 8batch读前、共享expert窗口cache文件锁、低网格FP32与3bit/bitpack无损证据、GPU完成case立即进入CPU进程计数；合计分析最多16进程且受quota限制，每数值库1线程。内存预算256GiB且≤实际可用50%，≥32GiB可用内存、各GPU至少16000MiB空闲、缓存/证据磁盘预留600GiB。资源不符停止准备，不强占剩余显卡或改batch。24–48h预留窗口，实际ETA待首批校准，无填时长追加实验。

启动脚本enqueue_phase2.py复用原完成快照、逐文件验SHA及固定Git提交生成独立目录 /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase2_matched_<time>_<pid>。先检查Phase1.5完整完成、进程/锁退出，唯一登记；再次调用只显示既有目录。用户执行一次性bootstrap后回传PHASE2_REGISTERED/PHASE2_LOG，再只读status_phase2.py。旧enqueue/accelerate不用于本轮；中断/故障保留目录，不能靠重复enqueue恢复。

无SSH、Test6/held4/final或自动失败配方重跑；主线仍双向条件互补/退化缺失，恢复旁支。已知missing硬回退保护与unreported corruption的动态选择分开；oracle不是方法或mIoU上界。训练输出本地源码/计划不代表论文成功，最后旧服务器查询仍2026-10-13T11:35:58.181880+08:00，原Phase1.5完成观测11:31:16.761032。上传9d7c27e8及b3546315/3ce2495原件与设计均保留。

新上传器完成后前台执行upload_phase2.py：精确JSONL gzip分块base64+manifest/summary，逐文件索引与SHA保留在流内；checkpoint/大数组/完整log留服务器。认证失败复用既有worktree，不重复快照、不force push。

