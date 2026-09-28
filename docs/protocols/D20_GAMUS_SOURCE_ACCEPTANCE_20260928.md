# D20 新候选来源：修订版 GAMUS Stage A 准入

## 为什么新增候选

原计划首选 US3D/DFC2019 Track 1，但服务器没有原始三元组，官方页面受代理 403，原始包第三方中转与科研发表条件仍待确认。经查[作者 GAMUS 仓库](https://github.com/EarthNets/RSI-MMSegmentation)，修订版公开说明已从其数据中移除 DFC2019 的 Omaha/Jacksonville 样本，理由是标签质量。修订版数据由作者仓库链接到[公开的 Hugging Face GAMUS](https://huggingface.co/datasets/earthflow/GAMUS)，页面标有 CC BY 4.0。原[论文](https://arxiv.org/abs/2305.14914)描述配准的 RGB、nDSM 与语义标签；当前公开版本及其来源须以实际文件重新核查，不能直接沿用论文旧版的城市数和指标。

2026-09-28 的公开 Hub 元数据预查显示，修订版固定 revision `a3c0e2511f06d909612406f436cf8abb4da805f5` 下，`images`、`heights`、`classes` 三组文件在 train/val/test 的城市计数相同：

| 原划分 | DC | NYC | PHL | 每模态文件数 |
|---|---:|---:|---:|---:|
| train | 1,439 | 1,167 | 2,398 | 5,004 |
| val | 359 | 0 | 500 | 859 |
| test | 361 | 1,000 | 1,500 | 2,861 |

这些只是元数据计数；尚未在服务器打开数据。**原划分混合城市，不能直接当作跨城市最终验证。** 后续必须依据来源与地理信息重新冻结 fit/dev/final，且避免同城相邻块与重复影像泄漏。标签无 Car；这项来源若通过也只能回答高度模态的外部有效性，不能确认 Potsdam 的 Car 结论。

## 本次执行边界

Stage A 脚本只在 `/home/jovyan/zzx` 内存放数据与记录，CPU 运行：

1. 锁定作者链接的公开数据 revision，读取 Hugging Face API 全部文件名、大小与 LFS SHA；验证三模态每个划分的文件名 ID 一一配对，不使用 viewer 报告的行数代替文件数。
2. 每城只下载一组 RGB/AGL/CLS HDF5 小样本（DC 与 PHL 来自原 train，NYC 来自原 test），逐文件限制 16 MiB，并校验公开 LFS SHA。
3. 只读 HDF5 `image` 数据集，记录形状、类型、有限值、类别像素统计和三模态空间尺寸；不把原 test 当作冻结的外部 final。
4. 汇总 `SAMPLE_CONTENT_PASS_SOURCE_ACCEPTANCE_PENDING` 或 `SAMPLE_CONTENT_REVIEW_REQUIRED`。即使小样本通过，也**未**完成来源权利、数据质量、地理切分和正式 GPU 协议准入。

GAMUS Hub 的 CC BY 4.0 是数据卡上的声明；仍需核对原 DC/NYC/PHL 影像、LiDAR 和标签的来源及授权，不能单凭标签认为全部上游权利已清楚。未批准新训练矩阵，Vaihingen seed42 失败及不补 seed17 的判断保持不变。DFC2019 原始包不经 GAMUS 旧版链接或第三方镜像绕过已有条款。

## 服务器运行

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
conda activate remote_sensing
git pull --ff-only origin rebuild-v1-protocol-20260915
bash scripts/run_rebuild_v1_d20_gamus_source_audit.sh
```

脚本只获取作者新版本中 9 个小样本；若环境缺少 `h5py`，会在下载前停止并记录失败状态。样本保存在 `/home/jovyan/zzx/datasets/rebuild_v1_d20_gamus/`；完整审计与日志位于项目 `records/rebuild_v1_d20_gamus_source_acceptance_20260928/`，适合跨电脑接力的 JSON、状态和运行绑定复制到 `records/rebuild_v1_d20_gamus_source_acceptance_compact_20260928/`。GitHub 不归档原始 HDF5。

完成后检查 `audit.json` 的状态、三城三元组和原划分计数，再提交紧凑证据：

```bash
git add records/rebuild_v1_d20_gamus_source_acceptance_compact_20260928
git diff --cached --check
git commit -m "Archive D20 revised GAMUS source audit"
git pull --rebase origin rebuild-v1-protocol-20260915
git push origin rebuild-v1-protocol-20260915
```

下一决策：若样本或权利不合格，保留失败证据并返回其他候选；若合格，先审计**全量地理来源与类别覆盖**并冻结新城市级切分、训练预算与门槛，再开展匹配短流程。不得直接复用旧 GAMUS 官方 train/val/test 或基于最终城市成绩选模。
