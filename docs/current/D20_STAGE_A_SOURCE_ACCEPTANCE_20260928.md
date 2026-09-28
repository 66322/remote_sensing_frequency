# D20 Stage A：独立来源准入检查（US3D / DFC19）

## 当前状态

- Date: 2026-09-28
- Protocol: `docs/protocols/D20_INDEPENDENT_SOURCE_AND_MATCHED_BASELINES_20260928.md`
- Status: **SOURCE_FIT_PASS / LOCAL_TRIPLETS_ABSENT / TRANSPORT_TECHNICALLY_AVAILABLE / TERMS_FOR_RELAY_PENDING**
- Server probe: 2026-09-28 15:22 +08:00, executed commit `6c7c0d1`; compact result is in
  [`user_reported_stage_a.json`](../../records/rebuild_v1_d20_source_acceptance_compact_20260928/user_reported_stage_a.json)
- GPU queue: none
- Test6: sealed; not loaded
- Google Drive: the previously failed proxy-403 route is explicitly excluded from the new probe
- Current action: [confirm access, private-relay permission and publication procedure](D20_US3D_ACCESS_AND_USE_INQUIRY_20260928.md)

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

以下是服务器实测前的候选选择；实测结果及当前执行边界见文末更新：
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


## 2026-09-28 15:22 +08:00 服务器实测更新

服务器在 commit `6c7c0d1` 执行 Stage-A source audit 成功，结果为
`BLOCKED_DATA_TRANSFER_AND_TERMS_PENDING`：

- 本地 DFC19 TIFF：0；RGB/AGL/CLS 三元组：0。
- GRSS 与 IEEE DataPort 从服务器访问均被代理返回 403；这是网络访问阻塞，不是数据不合格。
- 官方 JHU/APL GitHub Track-1 torrent metadata 可达（HTTP 200），SHA256
  `7ef1c26b14ed66e257e549c4278f053ac8cb582d477bce738e333b074572a028`。
- Track-1 torrent 总量约 48.68 GB；D20 实际仅需
  `Train-Track1-RGB.zip` 7,073,992,673 bytes 与
  `Train-Track1-Truth.zip` 8,774,684,120 bytes，合计 15,848,676,793 bytes。
- 服务器剩余约 5,769.96 GiB，因此存储不是阻塞。
- GPU 未使用，Test6 未加载，Google Drive 未重试。

下一步不是立即启动 BitTorrent 下载。2019 DFC 条款禁止注册用户分发数据包，
而常规 BitTorrent 客户端在下载中可能上传 pieces；先运行
`scripts/run_rebuild_v1_d20_torrent_route_preflight.sh`，检查 torrent 是否包含
HTTP webseed，以及官方 tracker 的直接传输可达性。该预检不会 announce、不会请求
数据块、不会上传或下载数据包。若没有无上传的直接路线，优先走注册后的
DataPort/数据所有者直接下载，再将来源和条款状态写入 Stage-A 记录。


## 2026-09-28：Hugging Face / Colab 中转路线更新

用户确认该服务器此前已经成功通过 Hugging Face 下载大型数据；既有成功流程包括
Colab/外部网络获取数据后，经 Hugging Face 私有 dataset repo 中转，再由服务器使用
`huggingface-cli download ... --repo-type dataset --local-dir ...` 拉取。因此从纯技术角度，
当前 GRSS/DataPort 代理 403 **不再视为服务器无法获取外部数据的最终阻塞**。

但是 DFC2019 官方条款明确禁止注册用户 dissemination/distribution of the data packages。
把 `Train-Track1-RGB.zip` / `Train-Track1-Truth.zip` 上传到 Hugging Face（包括 private repo）
会把原始受限数据复制到第三方平台，是否属于被禁止的 distribution 不能自行假定允许。
因此当前执行边界为：

- Hugging Face/Colab 作为 **已验证可工作的技术传输能力** 记录；
- 未取得数据方/GRSS 对此中转方式的许可前，**不上传 DFC2019 原始 ZIP 到 Hugging Face**；
- `torrent_route_preflight` 降为备用诊断，不再是当前优先执行项；
- Stage A 当前准确状态改为 **SOURCE_FIT_PASS / TRANSPORT_TECHNICALLY_AVAILABLE / TERMS_FOR_RELAY_PENDING**；
- 若获得许可，可直接复用既有 HF 私有 dataset relay，不需要再解决服务器到 GRSS/DataPort 的代理 403；
- GitHub 只保存脚本、清单、哈希、路径和实验结果，不保存 DFC2019 原始数据。

下一项 Stage-A 工作因此改为：确认官方注册/科研使用审批以及是否允许个人私有云/HF 中转。
在此之前不启动 GPU，也不切换 Houston；US3D/DFC19 仍是第一候选。

## Vaihingen 的可用角色

用户服务器已有 Vaihingen。此前元数据审计确认 17 个旧实验未用 ID 有提取的
光学、DSM、完整标签文件；但这些 patch 与已用于旧 F0/P1 训练和评价的区域同属
一幅影像镶嵌图，且交错或相邻，故不能仅凭 ID 未使用就称为独立最终验证。
已有 ID、历史曝光和文件说明见
[D9B 来源记录](D9B_SOURCE_STATUS_20260923.md)。

Vaihingen 很适合在等待 US3D 条款/传输期间做低成本的数据管线、类别映射、
输入退化和 P0/P1/P2 短流程开发，但结果须明确标为同域探索。正式使用前仍要核对
实际标签路径、边界标签版本、内容对齐、场景相邻关系与既往曝光。官方 Vaihingen
TOP 三个通道是**近红外、红、绿**，并非真 RGB；将其送入现有 DINO RGB 预训练
模型会改变输入含义，应单独冻结通道方案和归一化，不能直接套 D20 US3D 的 RGB
结论。[ISPRS 数据说明](https://www.isprs.org/resources/datasets/benchmarks/UrbanSemLab/2d-sem-label-vaihingen.aspx)

如后续 US3D 确定不可用，可单独制定 Vaihingen 探索协议；其结论等级不能写作
跨城市独立最终确认。
