# 当前状态：Phase2 CE技术替换已登记，待查询新队列（2026-10-13）

## 最新：技术替换已登记（用户终端回执）

2026-10-13 15:11（Asia/Shanghai，目录/日志时间；不是status查询）：PHASE2_TECHNICAL_REPLACEMENT_OF原145903目录，PHASE2_REGISTERED新目录 `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase2_matched_20261013T151120_1310582`，controller PID **1310878**，执行代码 **e5641e073bf4421e346f589199c291a6e94db8b2**，GPU0/1。日志 `nohup_20261013T151123110536.log`。核心4训练48k、最多6训练64k、无24h截止。原失败目录完整保留。

新队列已登记；准备完成、修复CE真实GPU核验、双卡batch16 smoke通过及正式训练状态均尚无新status证据。下一步仅查询新目录code/scripts/status_phase2.py并读取上述nohup日志，勿再次enqueue/技术替换。下方15:02状态和“待执行/尚未登记”描述属于这次回执之前的历史；新登记不代表GPU验证或训练成功。回执：[原件](../../records/phase2_ce_fix_20261013/replacement_registration.txt)。

最后服务器查询 **2026-10-13T15:02:06.544744+08:00**：原Phase2为TECHNICAL_FAILURE_HOLD，controller/worker均退出；prepare与legacy_counts完成，两卡smoke均在CUDA交叉熵确定性归约失败，正式训练尚未派发。原目录 `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase2_matched_20261013T145903_1304150`，代码f01f9e94，PID1304554是旧已退出进程。smoke1 RUNNING仅旧状态残留，不能当实时运行。

修复已实现：保持严格确定性及原mean CE/ignore255，改为classwise log_softmax/where归约；12项CPU检查通过，尚未在真实GPU验证。下一步用户显式执行enqueue_phase2.py --replace-ce-bug-directory指定上述原目录；专项门禁确认零训练产物、双卡同一缺陷、源封印不变且无活进程/锁后，在独立目录重新准备和双卡smoke。旧目录原件保留。**历史：修复后的新队列当时尚未登记**；不得直接重启旧controller、重复普通enqueue或自行重跑其他失败配方。

[技术修复协议](../protocols/PHASE_2_CE_TECHNICAL_FIX_20261013.md)、[完整执行协议](../protocols/PHASE_2_EXECUTION_20261013.md)、[科学设计](../protocols/PHASE_2_MATCHED_COMPLEMENTARITY_20261013.md)、[原始失败日志](../../records/phase2_ce_fix_20261013/server_smoke_failure.txt)、[修复CPU验收](../../records/phase2_ce_fix_20261013/verification.json)。用户启动后回传PHASE2_TECHNICAL_REPLACEMENT_OF/PHASE2_REGISTERED/PHASE2_LOG，再只读查询新目录status。无SSH，服务器由用户操作。

研究决定保持RGB–DSM双向条件互补与退化/缺失分割主线，任务驱动恢复旁支。这次是工程兼容性修复，不是研究假设失败或新方法正结果。核心A_RGB/A_DSM各16k与B0/B2各8k（4训练48k），C/L、静态剩余差距及保护通过才派B1/B3（最多6训练64k）；seed42、Fit12/Val2、GPU0/1、24–48h资源窗口但无截止。未知缺失动态选择与已知缺失硬回退分别报告，oracle不是可部署方法或mIoU上界。未访问Test6/held4/final，不增加seed。

资源继续只读输入驻留/mmap、crop8/prefetch8、冻结窗口cache复用、GPU case完成即CPU多进程原始计数；分析合计最多16进程且受quota约束、数值库单线程，256GiB热缓存上限且不超过可用内存50%。启动校验至少32GiB可用内存、各卡16000MiB空闲、600GiB磁盘预留。修复损失在全部专家/融合头统一使用。进度和执行快照在/home/jovyan/zzx对应records独立目录；完成前台upload_phase2.py无损分块原件，数组/权重/完整log留服务器并索引。
