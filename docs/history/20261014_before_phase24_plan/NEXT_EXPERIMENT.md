# 下一步：执行已授权清理，再解释剩余互补（2026-10-14）

## 后续缓存策略：用完即删（用户2026-10-14明确要求）

默认避免整轮落盘，优先有界内存/分批预取，磁盘缓存须有必要性和容量上限、登记消费者，最后消费者使用完立即删除；评估优先直接留原始计数，减少整图预测。新队列启动前必须落实并验证数值/数据流和清理路径，不能仅沿用旧全量缓存设计。[执行规则](../protocols/EXPERIMENT_ARTIFACT_RETENTION_20261013.md)。当前Phase2大型缓存已清理，冻结快照不改；新的即时回收实现尚未建立，不写成自动执行完成。

## Phase2产物清理已完成（用户回执2026-10-14 12:13:25）

complete.json deleted/total=35910/35910，observed_at2026-10-14T12:13:25.974504+08:00，receipt：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase2_matched_20261013T151120_1310582/artifact_cleanup_20261014T120418_1928998。源SUMMARY：35910独立inode、752849031168 bytes（701.1453GiB）预计完全断链，外部硬链接0；evaluation26698、head_cache8000、val_cache1212。四项服务器测试和24643上传原件复核通过后删除。

disk_free_before4461560856576、after4751404040192，整挂载盘净增289843183616 bytes（269.9375GiB）。净变化与清单预计断链不同，未隔离同期整盘活动/存储记账，不将431GiB差额断言为其他实验写入。四轮累计111906路径、清单预计完全断链2.60719TiB，非净实测回收量。

原CM/轨迹/代码配置/权重/输入/上传包与tail坐标数组按脚本保留；普通cache/compact预测已退役，原array complete SHA路径不再在线。progress.json最后35800是每200项刷新残留，以complete35910为准。不重复启动清理。下一步仍为旧D23缓存/遗留support数组/无依赖中间权重的精简核对，及研究剩余差距；本轮不启动新训练。[精确回执](../../records/phase2_review_20261014/artifact_cleanup_receipt_121325.json)。下方未执行文字为历史。

1. [Phase2产物退役](../protocols/PHASE_2_ARTIFACT_RETIREMENT_20261014.md)：用户服务器执行固定运行目录的cleanup_phase2_completed.py --execute。只删已登记缓存/compact数组，保留计数、L坐标数组与必要权重。代码4项本地检查通过，尚未服务器执行；回传SUMMARY/CLEANUP_COMPLETE核对实际大小。
2. 旧D23缓存/1568跳过原因、660support嵌套预测、中间权重按实际依赖精简，不重跑旧删除脚本、不全目录清空。
3. [科学复核](../experiments/PHASE_2_RESULTS_20261014.md)：公平专家互补存在，静态未改善P-U且L信号/clean保护失败。当前已停止动态派发；下一协议聚焦弱DSM混合损伤与可观测剩余结构，未登记新训练。

用户允许及时清理预登记无用途产物，不再次重复问许可；服务器由用户执行，无SSH/额外seed/Test6/held4。新控制器必须落实生命周期清理，旧冻结快照不改。
