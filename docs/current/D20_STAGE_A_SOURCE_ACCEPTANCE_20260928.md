# D20 Stage A：独立来源准入检查（US3D / DFC19）

## 当前状态

- Date: 2026-09-28
- Protocol: `docs/protocols/D20_INDEPENDENT_SOURCE_AND_MATCHED_BASELINES_20260928.md`
- Status: **OFFICIAL_DOCUMENTATION_VERIFIED / SERVER_DATA_ACCESS_PENDING**
- GPU queue: none
- Test6: sealed; not loaded
- Google Drive: the previously failed proxy-403 route is explicitly excluded from the new probe

## 已确认的来源适配性

优先候选保持 **US3D / 2019 IEEE GRSS Data Fusion Contest Track 1**。

Track 1 训练数据原生包含：
- RGB input
- AGL (above-ground-level height, meters)
- CLS semantic labels

官方 JHU/APL baseline 采用同名 stem 的 `_RGB.tif`、`_AGL.tif`、`_CLS.tif`，
图像尺寸为 1024×1024。标签按 LAS code：Ground=2、Trees=5、Buildings=6、
Water=9、Bridge/elevated road=17、Unlabeled=65。**没有 Car 类别**，因此 D20
只能验证“高度模态是否在新地域仍有稳定价值”，不能验证 Potsdam 的 Car / 小目标结论。

US3D 覆盖 Jacksonville (JAX) 与 Omaha (OMA) 两个城市。官方竞赛页说明训练区有
ground truth，而 validation/test ground truth 不公开；因此 D20 只能从可访问的
训练区域内预先冻结 fit/dev/final 地理划分，不能依赖原竞赛隐藏 test label。

## 使用条件

2019 DFC 官方条款说明：
1. 数据包不得由注册用户再次传播；
2. 科学论文使用需要 IEEE GRSS IADF TC 和数据所有者逐案批准；
3. 论文需按官方名称、引用和致谢要求使用该数据。

因此“数据能下载”与“数据可直接用于论文发表”是两个门槛。D20 在正式训练前需把
publication-use approval 状态记录到准入报告；若只用于本地可行性筛选，也不能把
未经确认的再分发数据提交到 GitHub。

## 官方获取路线

JHU/APL 的 `pubgeo/dfc2019` 仓库公开提供所有 track 的 torrent metadata，并明确写明
数据也位于 IEEE DataPort 的 DFC2019 open-access 页面。对 D20 只需要 Track 1 的
**Train-Track1-RGB** 与 **Train-Track1-Truth**；MSI、Track2/3/4、隐藏 test truth
都不需要。

旧 `scripts/acquire_rebuild_v1_d10_dfc19.py` 使用 SynRS3D 作者的 Google Drive
`DFC19.zip`，服务器于 2026-09-23 遇到 proxy tunnel 403。D20 不再原样重试它。

## Houston fallback 判断

2018 Houston 数据含 5-cm RGB、0.5-m LiDAR DSM 和 0.5-m 20-class training labels，
但公开 ground truth 只覆盖一个 training region，测试 ground truth 未公开。
它有 Cars 类，但空间独立 fit/dev/final 的证据强度明显弱于 JAX/OMA 双城市 US3D。
此外同样存在论文使用审批要求。

因此当前策略保持：
- **US3D：内容适配 PASS_WITH_LIMITATIONS；访问/许可 PENDING。**
- **Houston：只在 US3D 服务器访问或许可明确不可行后检查一次。**
- 当前还不能把阶段 A 写成“可用”，也没有理由判为“不合格”；状态应为 **BLOCKED_PENDING_ACCESS**。

## 已加入的服务器检查

运行：

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
git pull --ff-only
bash scripts/run_rebuild_v1_d20_stage_a_source_audit.sh
```

该流程：
- CPU only；
- 不访问历史 Test6；
- 不启动训练；
- 不重试 Google Drive；
- 检查本地是否已有 `RGB/AGL/CLS` 三元组；
- 探测 GRSS / DataPort / 官方 GitHub torrent metadata；
- 下载的仅是很小的官方 `.torrent` 元数据文件；
- 解析 torrent 内文件名和大小，定位 Track-1 RGB/Truth 包；
- 输出 `records/rebuild_v1_d20_source_acceptance_20260928/source_audit.json`。

## Stage-A 退出规则

1. **LOCAL_TRIPLETS_PRESENT...**  
   进入下一步 raster header / class / coordinate / split audit，再决定 B 阶段。
2. **BLOCKED_DATA_TRANSFER_AND_TERMS_PENDING**  
   说明官方 metadata 路线可达，但数据包/使用审批仍未落实；只解决这两个阻塞，
   不跑 GPU。
3. **BLOCKED_NO_WORKING_SERVER_ACCESS_ROUTE**  
   半天检查点到此为止，检查 Houston 一次；仍不通则暂停独立来源训练路线。

本文件只冻结“来源事实 + 执行入口”，不会提前冻结 fit/dev/final tile ID；
地理 ID 必须由实际 Track-1 文件清单与坐标覆盖检查后再写死。
