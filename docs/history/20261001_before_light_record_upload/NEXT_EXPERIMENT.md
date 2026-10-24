# 下一步：补已有工程摘要绑定，再准备正式资源锁

1. 只读records/research_d23_b_engine_admission_20261001T140528_658274中gpu0/gpu1的summary.json、preflight.json和cpu_checks.log。输出status/mode/observed_at/UUID/torch/源码和专家SHA、反传方式、各组更新数/耗时、条件列表/尺寸/原计数合计、峰值内存/显存及fallback。轻量原件归档和索引留同目录，回传紧凑JSON用于GitHub核验；不重跑实验。
2. 核对GPU0 smoke八组/14条件与服务器CPU22测试、GPU1 profile单次backward与训练tile整图3条件、重载/缺失回退/设备/时钟。当前粘贴尾部只覆盖两缺失条件及部分TSF片段，不能替代完整身份验收。[已核对范围](../experiments/D23_B_ENGINE_TAIL_AUDIT_20261001.md)。
3. 完整绑定通过后，测12tile磁盘缓存/TCAP统计I/O及双卡并行预算；按当前源码冻结wall/job/磁盘与资源锁，才生成8组各4000步队列。当前正式锁/队列未生成，无正式训练。
4. 按冻结screen比较真实精度/机制/风险，不把训练tile工程指标作为开发Val2或论文test结果。失败保持原门槛，允许关闭解法/撤回频率承诺，不自动续训或补seed。

所有共享记录直接更新本GitHub分支，见[两电脑记录规则](../protocols/RECORD_SOURCE_AND_HANDOFF.md)。本地不是权威状态来源。全部服务器产物仍在zzx对应实验目录；禁止读取旧Test6。

只读工具：scripts/collect_rebuild_v1_d23_engine_records.py；从固定提交提取到本次已有实验code/scripts，读取已有文件并在该实验目录生成compact_review及light_engine_evidence归档。无GPU依赖、无新数据加载。
