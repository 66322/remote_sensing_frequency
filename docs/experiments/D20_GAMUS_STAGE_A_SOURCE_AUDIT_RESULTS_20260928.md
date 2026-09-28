# D20 修订版 GAMUS Stage A 来源小样本审计结果

## 结论与证据

**状态：`SAMPLE_CONTENT_PASS_SOURCE_ACCEPTANCE_PENDING`。**服务器在 2026-09-28 18:33:49 +08:00 完成 CPU 审计，退出码 0。执行代码为 `83808a96f64e3bc5b8986dbfd1d11cfd6e803239`，结果归档于 `70344a4`。原始紧凑证据：[audit.json](../../records/rebuild_v1_d20_gamus_source_acceptance_compact_20260928/audit.json)、[status.tsv](../../records/rebuild_v1_d20_gamus_source_acceptance_compact_20260928/status.tsv)、[run_context.txt](../../records/rebuild_v1_d20_gamus_source_acceptance_compact_20260928/run_context.txt)。本报告复核归档记录，未重新读取服务器 HDF5 原件。

数据固定于 `earthflow/GAMUS` revision `a3c0e2511f06d909612406f436cf8abb4da805f5`。文件名清单的 `images`、`heights`、`classes` 在原 train/val/test 内一一配对，每种模态对应 5,004／859／2,861 个文件；三个原划分都混有城市。DC、PHL、NYC 各一组影像／高度／标签 HDF5 样本通过文件哈希、1024×1024 空间尺寸、有限值与类别内容检查。NYC 样本来自原 `test`，本次只用于来源读取检查，不作为独立最终评价。

前两次尝试分别因缺少 `h5py`、Hub API 分页参数 HTTP 400 在样本下载前停止；第三次复用记录目录中的隔离依赖并完成。状态表保留三次尝试。归档 `audit.json` 标记 `gpu_used=false`、`training_started=false`、`potsdam_test6_loaded=false`。

## 准入边界与下一步

本次只验证三城各一组样本和文件名配对，**不等于全量数据或论文使用准入**。Hub 的 `cc-by-4.0` 是页面元数据；DC／PHL／NYC 原影像、高度和标签的底层权利与地理来源尚未核实。全量类别覆盖、相邻或重复影像泄漏、城市级 fit/dev/final 划分也未验收。原 GAMUS train/val/test 混城，不能直接充当跨城市最终验证。

下一步先做来源权利和地理信息核查，形成可审计的城市级划分及类别映射草案；随后再决定是否进行匹配短流程和 P0/P1/P2 训练预算。当前不启动 GPU。US3D/DFC2019 传输和使用条件仍待决；D20 Vaihingen seed42 的逐块门槛失败、不补 seed17 的决定不变，Potsdam Test6 继续封存。
