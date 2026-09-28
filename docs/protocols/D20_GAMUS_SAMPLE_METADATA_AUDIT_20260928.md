# D20 GAMUS 九文件元数据只读核查

## 目的与边界

使用已完成的 Stage A 审计绑定已下载的 DC、PHL、NYC 各一组三元组，仅检查九个 HDF5 文件根节点和 `image` 数据集的属性名与小型属性值，寻找坐标、投影或来源线索。先核对每个文件的大小和 SHA-256；不读取整幅像素数组、不下载文件、不启动 GPU、不改变训练环境。结果只用于判断文件内是否有可利用的元数据，**不能证明地理配准、原始权利或全量空间独立性**。

依赖既有 `records/rebuild_v1_d20_gamus_source_acceptance_compact_20260928/audit.json` 和服务器九个原样本。若 `remote_sensing` 缺少 `h5py`，复用 Stage A 记录目录中的隔离依赖；若依赖不存在则停止，不安装软件。输出写入新的 `records/rebuild_v1_d20_gamus_sample_metadata_20260928/`，紧凑证据复制至同名 `_compact_20260928/`。已有 `audit.json` 时拒绝重跑。

## 服务器执行

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
conda activate remote_sensing
git pull --ff-only origin rebuild-v1-protocol-20260915
bash scripts/run_rebuild_v1_d20_gamus_sample_metadata.sh
```

正常结束应显示 `SAMPLE_METADATA_INSPECTED_SOURCE_ACCEPTANCE_PENDING`、`files: 9` 和属性命中数。请把该终端输出与 `records/rebuild_v1_d20_gamus_sample_metadata_compact_20260928/audit.json` 归档到 GitHub，再判断是否具备从文件内恢复空间位置的线索。此审计没有后续自动训练步骤；城市来源与底层使用条件仍需向原始发布方核实。
