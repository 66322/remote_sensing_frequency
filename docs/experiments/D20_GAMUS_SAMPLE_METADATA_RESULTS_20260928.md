# D20 修订版 GAMUS 九文件 HDF5 元数据核查结果

## 证据与结果

服务器在 `ed4186a` 执行只读 CPU 审计；最后归档状态为 2026-09-28 22:17:36 +08:00、`AUDIT COMPLETE 0`，紧凑证据由 `4cdb91f` 推送。原始文件：[audit.json](../../records/rebuild_v1_d20_gamus_sample_metadata_compact_20260928/audit.json)、[status.tsv](../../records/rebuild_v1_d20_gamus_sample_metadata_compact_20260928/status.tsv)、[run_context.txt](../../records/rebuild_v1_d20_gamus_sample_metadata_compact_20260928/run_context.txt)。本机对九条记录逐一核对了前次 Stage A 的城市、模态和 SHA-256 绑定，并复查属性字段汇总，结果通过；没有重新读取服务器原始 HDF5。

DC、PHL、NYC 各一组 RGB、AGL、CLS，共九个样本。每个 HDF5 根节点只含 `image` 数据集；根节点及 `image` 数据集的属性字典全部为空。`files_with_possible_geo_or_source_attributes=0` 不只是关键词未命中，而是这九个样本在所查的两个层级没有任何属性。审计没有下载数据、读取整幅像素数组或启动 GPU。

## 解释边界

这九个样本自身不提供可读取的 CRS、仿射变换、地理范围或原始发布者属性；不能从文件内直接建立文件名到地图坐标的映射。结果不证明全部 GAMUS 文件都没有元数据，也不证明影像／高度／标签已严格配准，更不构成原始数据权利判断。城市前缀只说明作者的城市归类，不足以排除同城相邻块或重复块泄漏。NYC 样本来自原 `test`，本次仅用于来源技术核查，不作为模型最终评价。

## 下一准入证据

在设计独立地域 fit/dev/final 前，需从作者或原始发布方取得并核对：

1. DC、PHL、NYC 每城 RGB 正射影像、LiDAR／高度及类别标签分别对应的原始数据集、发布者、获取时间和许可或使用条件；修订版 GAMUS 的再发布与论文使用条件。
2. 每个发布文件名／stem 对应的地理范围、CRS、原始瓦片 ID 或可复现的裁剪规则；同城不同 split 是否存在邻接、重叠或重复。
3. 三城的类标映射、无效值和全量类别覆盖；此项还未由九文件探针验收。

公开[作者仓库](https://github.com/EarthNets/RSI-MMSegmentation)链接修订版数据；旧[论文数据收集段](https://arxiv.org/html/2305.14914v1)概述 DC 和费城来源，但不能逐文件解释修订版 NYC 及三城底层权利。当前状态仍是 **`SOURCE_ACCEPTANCE_PENDING`**。在上述来源和地理证据不足时，不冻结最终区域、不启动 P0/P1/P2 新 GPU 训练；D20 Vaihingen seed42 的失败门槛及 Test6 冻结不变。
