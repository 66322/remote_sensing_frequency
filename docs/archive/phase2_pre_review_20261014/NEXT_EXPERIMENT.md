# 当前记录：Phase2 B0评估与历史预测清理（最后观测2026-10-13 19:36）

## 最新Phase2查询：2026-10-13 20:46:59

用户status QUERY20:46:59.695116/LAST20:46:59.387908：EVALUATING_B0_16000，controller LIVE=True，GPU0/1 eval_B0 workers1441905/1441906均RUNNING/LIVE=True。A_RGB/A_DSM各16k、B0/B2各8k COMPLETE，平均融合8k/16k评估、gates及两head_cache完成。B0/B2训练19:35:49结束；到此次查询约71分钟仍在B0评估，不代表卡住，需要evaluation case completion/window progress核对。

已回读冻结执行e5641e07 control_phase2/phase2_analysis：B0评估→B2评估→static_gate→summary。allow_dynamic严格需要C与L均True；现打印C=True/L=False，因此在门禁文件不变且流程正常的条件下不会派发B1/B3，非“可能再补2训练”。不改门禁、不增加训练。当前status未提供case完成数，无法可靠绝对ETA；需只读统计B0/B2 counts/complete及与已完成average_16000同面板case数，避免凭训练ETA估整轮。最新观察原件摘要见records/phase2_progress_20261013/observation_204659.json。

## 后续实验及时清理为用户明确要求（2026-10-13）

用户授权实验跑完及时删除不再需要的中间产物。[保留与生命周期规则](../protocols/EXPERIMENT_ARTIFACT_RETENTION_20261013.md)已更新：新控制器派发前须实现登记清单、最后消费者释放后的缓存清理、原始计数核验后的无用途预测清理、选模/下游完成后的中间权重清理以及清理回执。默认不批量永久保存各条件/参考分支整图。保留最终原始计数/配置/代码/轨迹/必要权重，无需为预登记临时文件再逐次确认。当前冻结Phase2尚无自动清理，须查询消费者和原始结果后独立执行，不能改源封印或宣称已自动删除。

## 第三批已完成（用户终端回执，目录时间2026-10-13 20:10:11）

CLEANUP_COMPLETE 22824；receipt `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/storage_prediction_cleanup_third_20261013T201011_1459275`。三批累计删除75996路径。用户df显示挂载盘10T、已用6.3T、可用3.8T、63%，不是zzx自身大小，也不代表独立测得回收量。尚未收到第三批SUMMARY及complete.json精确前后字节。

候选24392比实际删除多1568，数量恰好等于D23 evaluation预测组，但原因仍须读取plan.skipped验证，不能断言缺计数或丢失。下一步只读当前receipt的summary、跳过原因计数/样例和complete；不重复运行删除。D23 normalized_fit_cache68.4GiB、全部权重及其下游依赖仍待核对，未删除。当前Phase2状态仍仅19:36观测。

## 六个旧实验盘点完成；第三批预测清理已准备（2026-10-13，源目录时间20:04:42）

用户回传AUDIT_COMPLETE，六目录全部errors=0，源records/storage_old_experiments_audit_20261013T200442_1456518。主要占用为jobs/evaluation、fixed8000、N5 content_*、D30 replay modes预测；样例均Val2 uint8 6000²。另D23 normalized_fit_cache360个数组68.4GiB；权重较小，本批不动。组内统计未跨组inode去重，禁止直接加总当可回收量。

第三批脚本delete_audited_old_predictions.py已通过15项本地检查，服务器未执行。按源manifest核对文件身份/头、对应JSON整数6×6原始计数、进程依赖，执行时统一inode核算后只删匹配预测。缺计数跳过、文件变更停止；保留全部权重/代码/JSON/log/shared_reference/训练缓存和当前Phase2。[协议](../protocols/HISTORICAL_PREDICTION_THIRD_CLEANUP_20261013.md)。下一步用户执行并回传SUMMARY/CLEANUP_COMPLETE；D23缓存及中间权重留待进一步依赖核对，不将尚未清理写成完成。

## 用户更新保留策略：大型旧实验精简保存（2026-10-13）

用户要求继续核对其他大型旧实验，仅保留有用最终结果和代码。已据此记录[产物保留规则](../protocols/EXPERIMENT_ARTIFACT_RETENTION_20261013.md)：保留可重算指标的原始计数、配置/代码及必要selected/final/下游权重，优先退役可再生成数组与无依赖中间产物；不能将负结果视为无价值证据。旧代码按条件×输出×checkpoint反复保存整图且缺少结果验收后的清理闭环，后续新实验必须显式规划保留周期。当前Phase2不改冻结快照、不删运行缓存。

audit_old_experiment_storage.py已准备，三线程只读扫描六个大型旧实验，打印进度、逐阶段/扩展名占用与少量Val2头样例，并保存权重及证据索引。不扫描整个zzx，不删除。语法检查通过，服务器尚未执行；待用户回传summary形成精确清理清单。最新运行状态仍仅19:36，删除回执为19:47目录时间。

## 最新观测与清理下一步（2026-10-13 19:36）
用户终端扫描19:36:10–19:36:22：records=2957484469248 bytes（2.69TiB），不是整个zzx；挂载盘df10T/7.1T used/3.0T avail/71%。当前Phase2目录620860312576 bytes（578.2GiB），val_cache252110893056、head_cache243290112000、evaluation106213376000、inputs9792020480、jobs9448818688。两缓存约80%；此前约17G至此明显增长，但没有隔离整个挂载盘全部写入/回收来源，不能把净df变化完全归因某一任务。
队列最后查询19:36:10：EVALUATING_B0_16000，controller与GPU0/1评估worker存活；A_RGB/A_DSM/B0/B2 COMPLETE。这是终端观测，不是实时状态或最终科学验收。gates_C_L打印C=True、L=False、STOP_OR_INCONCLUSIVE，仍需轻量原件核验，不升级为研究方向结论。主线及门禁不变，勿重复登记或额外训练。
第一轮删除31956完成；剩余21876路径中预计21216位于已核对的fixed8000/support_fixed8000/initial_evaluation/stress_evaluation，第二批脚本已通过11项本地检查，**服务器尚未执行第二批**。直接从旧跳过清单核算并删除这部分旧Val2预测，剩余660嵌套路径保留样例待查。当前Phase2、权重和轻量证据保留；其他大型旧实验仅是审计候选，尚未授权按整目录清空。
[第二批执行边界](../protocols/HISTORICAL_PREDICTION_SECOND_CLEANUP_20261013.md)。下方更早运行/待执行描述仅属历史，以此时间戳优先。


## 磁盘盘点（2026-10-13用户提供，无精确查询时间）

df显示/home/jovyan容量10T、已用7.2T、可用2.9T、72%；这是整个挂载盘，不能用zzx占用解释全部7.2T。zzx 3.6T，paper_rebuild 3.2T，08_thesis_full_repro/records 2.8T。可用空间按现有约1TiB整轮预算暂有余量；状态会变化，不保证固定余量。[原始盘点](../../records/storage_inventory_20261013/user_disk_inventory.txt)。当前Phase2新目录当次du约17G，旧失败目录9.2G；这不是新的训练status。

优先只读拆分最大五目录：research_post_d30_mechanisms_20261004T000812_2446364 527G、research_post_n3_s1_20261007T083203_694293 292G、research_post_s1_support_20261008T234921_1890161 268G、research_post_s1_transfer_20261010T073327_2852696 251G、research_d27_safe_routing_repair_20261003T092243758628_2001983 233G；合计约1.5T，大小不构成可删除证明。继续查看它们一级子目录占用后核验完成/失败原件、共享SHA绑定及当前依赖，才形成精确清理清单。不提供整目录删除，不因GitHub轻量证据已上传就假定大数组/权重无需保留。当前Phase2、数据、预训练和旧被绑定证据保留，无任何服务器删除/移动行为。

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
