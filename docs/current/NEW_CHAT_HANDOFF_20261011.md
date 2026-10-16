# 新对话交接：Phase2 双卡smoke完成，配对专家正在训练（2026-10-13）

## 最新运行观测：配对专家正式训练已启动

用户查询 **2026-10-13T15:17:32.976199+08:00**，队列更新15:17:31.773714：TRAINING_MATCHED_EXPERTS，controller LIVE=True。新目录research_phase2_matched_20261013T151120_1310582，代码e5641e07，controller1310878。prepare/smoke0/smoke1/legacy_counts均COMPLETE；A_RGB GPU0 PID1312176和A_DSM GPU1 PID1312177均RUNNING/LIVE=True。RGB step2180/16000、loss0.2066975385、elapsed223.911s、remaining_train_hours0.394298；DSM step1740/16000、loss0.4762486219、elapsed222.290s、remaining_train_hours0.506044。最近data_wait约65/61ms，峰值分配2612352000 bytes，各卡reserved3107979264 bytes。

控制器已通过两卡smoke门禁并派发训练；目前依据用户status/日志，smoke数值原件、参数清单、batch_hash和验证指标仍待接收核验，不据此声称论文结果。估时约RGB24分钟、DSM30分钟为脚本纯训练步数外推；不含后续定期全图验证、冻结面板、head缓存/训练和CPU分析，不是整轮ETA。单步两loss不能比较模态优劣。两卡速度不同允许，无逐step屏障；完整配对stream在双方完成后验hash。只读查询既有新目录，不重启/登记。

**容量修正（源码估算，非服务器实测）**：600GiB仅启动下限，完整磁盘预算此前不足。按6000²、529窗口、保存FP32及紧凑原件，head缓存约227GiB、专家窗口cache约235GiB、核心面板原件约240GiB，外加checkpoint/输入等；核心建议750–850GiB，全6训练建议约1TiB。实际df尚未返回，不能保证磁盘充分。缓存无自动删除；核验/上传后明确清理清单，用户执行。保持正在运行配置，不自动删缓存、改batch或补训练凑24h。后续读取resource_profile实际free及df输出校准预算。

登记和修复前的等待描述均属下方历史。[本次观测](../../records/phase2_ce_fix_20261013/training_observation_151732.json)。

## 最新：技术替换已登记（用户终端回执）

2026-10-13 15:11（Asia/Shanghai，目录/日志时间；不是status查询）：PHASE2_TECHNICAL_REPLACEMENT_OF原145903目录，PHASE2_REGISTERED新目录 `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase2_matched_20261013T151120_1310582`，controller PID **1310878**，执行代码 **e5641e073bf4421e346f589199c291a6e94db8b2**，GPU0/1。日志 `nohup_20261013T151123110536.log`。核心4训练48k、最多6训练64k、无24h截止。原失败目录完整保留。

新队列已登记；准备完成、修复CE真实GPU核验、双卡batch16 smoke通过及正式训练状态均尚无新status证据。下一步仅查询新目录code/scripts/status_phase2.py并读取上述nohup日志，勿再次enqueue/技术替换。下方15:02状态和“待执行/尚未登记”描述属于这次回执之前的历史；新登记不代表GPU验证或训练成功。回执：[原件](../../records/phase2_ce_fix_20261013/replacement_registration.txt)。

最后服务器查询 **2026-10-13T15:02:06.544744+08:00**：原Phase2为TECHNICAL_FAILURE_HOLD，controller/worker均退出；prepare与legacy_counts完成，两卡smoke均在CUDA交叉熵确定性归约失败，正式训练尚未派发。原目录 `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase2_matched_20261013T145903_1304150`，代码f01f9e94，PID1304554是旧已退出进程。smoke1 RUNNING仅旧状态残留，不能当实时运行。

修复已实现：保持严格确定性及原mean CE/ignore255，改为classwise log_softmax/where归约；12项CPU检查通过，尚未在真实GPU验证。下一步用户显式执行enqueue_phase2.py --replace-ce-bug-directory指定上述原目录；专项门禁确认零训练产物、双卡同一缺陷、源封印不变且无活进程/锁后，在独立目录重新准备和双卡smoke。旧目录原件保留。**历史：修复后的新队列当时尚未登记**；不得直接重启旧controller、重复普通enqueue或自行重跑其他失败配方。

[技术修复协议](../protocols/PHASE_2_CE_TECHNICAL_FIX_20261013.md)、[完整执行协议](../protocols/PHASE_2_EXECUTION_20261013.md)、[科学设计](../protocols/PHASE_2_MATCHED_COMPLEMENTARITY_20261013.md)、[原始失败日志](../../records/phase2_ce_fix_20261013/server_smoke_failure.txt)、[修复CPU验收](../../records/phase2_ce_fix_20261013/verification.json)。用户启动后回传PHASE2_TECHNICAL_REPLACEMENT_OF/PHASE2_REGISTERED/PHASE2_LOG，再只读查询新目录status。无SSH，服务器由用户操作。

研究决定保持RGB–DSM双向条件互补与退化/缺失分割主线，任务驱动恢复旁支。这次是工程兼容性修复，不是研究假设失败或新方法正结果。核心A_RGB/A_DSM各16k与B0/B2各8k（4训练48k），C/L、静态剩余差距及保护通过才派B1/B3（最多6训练64k）；seed42、Fit12/Val2、GPU0/1、24–48h资源窗口但无截止。未知缺失动态选择与已知缺失硬回退分别报告，oracle不是可部署方法或mIoU上界。未访问Test6/held4/final，不增加seed。

资源继续只读输入驻留/mmap、crop8/prefetch8、冻结窗口cache复用、GPU case完成即CPU多进程原始计数；分析合计最多16进程且受quota约束、数值库单线程，256GiB热缓存上限且不超过可用内存50%。启动校验至少32GiB可用内存、各卡16000MiB空闲、600GiB磁盘预留。修复损失在全部专家/融合头统一使用。进度和执行快照在/home/jovyan/zzx对应records独立目录；完成前台upload_phase2.py无损分块原件，数组/权重/完整log留服务器并索引。
