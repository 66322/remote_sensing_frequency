# D20 Vaihingen 同域开发来源：内容检查入口

当前状态：**修正版服务器运行已完成，17/17 块通过开发来源内容采样检查。**
服务器于提交 `5c6283b` 运行，原始精简结果已归档于 `66ac041` 的
[`audit.json`](../../records/rebuild_v1_d20_vaihingen_content_compact_20260928/audit.json)。
全部 17 块 TOP 为三通道 uint8、DSM 为单通道，TOP/DSM/FullGT 像素尺寸各自一致；
DSM 样本均为有限数，FullGT 样本颜色均属于已有六类调色板。
本结论是 **CONTENT_SAMPLE_CHECKS_PASS_DEVELOPMENT_ONLY**。
所有地理 header 对齐字段为 `null`，表示坐标信息不足，不能证明地理对齐；
每块最多约10万标签像素采样，不能证明全部像素都合法。

`tiles.tsv` 的空错误字段曾产生行尾制表符，导致 `git diff --cached --check` 报错。
用户随后仍提交了原文件；后续修正提交清理了该文件并修复生成器，原始历史保留。

下一项是冻结 Vaihingen **同域开发短流程**的输入与切分：TOP 通道按近红外/红/绿
处理，确认 DINO 适配的三通道方案；从 17 块中事先指定训练/开发区域及旧实验
曝光说明，规范 DSM 归一化、FullGT/NoBoundary 的使用范围。完成这些后才启动
P0/P1/P2 匹配短流程。US3D 的跨城市最终确认路线继续单独推进。

以下保留首次路径错误和审计入口，供复盘。
失败记录已由服务器以 `5299318` 归档。17/17 均显示 TOP、DSM 存在，
错误仅是脚本把完整标签目录误写为 `gts_complete`；仓库既有代码实际使用
`gts_complete_full`。这次没有读到标签像素，不能判定 17 个区域的数据质量。
没有新训练或GPU队列。
本检查使用服务器现有 Vaihingen 文件；US3D 仍是跨城市最终确认的优先来源。
旧审计已确认 17 个候选 ID 有提取文件和相同尺寸，但尚未检查完整标签的
实际像素值、光学通道和 DSM 有限数值。旧脚本还曾把去边界标签选成“完整标签”。

本轮明确选取同一数据根目录下的：

- `top/top_mosaic_09cm_area<ID>.tif`
- `dsm/dsm_09cm_matching_area<ID>.tif`
- `gts_complete_full/top_mosaic_09cm_area<ID>.tif`

此目录沿用仓库现有 `scripts/audit_crossdataset_physical_frequency.py` 的完整标签路径。
若实际缺失，审计会列出各根目录的缺项并标记 `REVIEW_REQUIRED`；
不会用 `gts_complete_eroded/*_noBoundary.tif` 顶替。
每块读取影像核对尺寸、通道和 DSM 样本有限值；标签采样最多约10万像素，
统计已知颜色及未知颜色。标签采样通过不能证明全部像素合法；缺少可读地理
坐标时，只能确认像素尺寸相同，不能声称已证明空间对齐。

在服务器项目目录，先拉取本分支最新提交，然后重跑：

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
conda activate remote_sensing
git pull --ff-only origin rebuild-v1-protocol-20260915
bash scripts/run_rebuild_v1_d20_vaihingen_content_audit.sh
```

该任务只用 CPU，读取 Vaihingen，不打开 Potsdam Test6，不下载数据，也不训练。
结果在 `records/rebuild_v1_d20_vaihingen_content_20260928/`；精简交接副本自动写入
`records/rebuild_v1_d20_vaihingen_content_compact_20260928/`，含执行 HEAD、
状态、`audit.json` 和逐块 `tiles.tsv`。若审计返回非零，精简副本仍保留供排错。
`status.tsv` 保留两次运行状态；首次失败原件也保存在 Git 历史提交 `5299318`。
将精简副本提交并推送到同一 GitHub 分支，另一台电脑才能看到实际判断。

通过的 ID 仅能用于**同一镶嵌图上的开发实验**。旧 F0/P1 已用部分场景，
其余场景与它们交错或邻近；没有独立最终确认集。Vaihingen TOP 通道为
近红外、红、绿；若随后做冻结 DINO 适配短流程，需单独冻结输入通道与
归一化方案，不能把结果称为 D20 US3D 的 RGB 跨地域复验。

历史来源与限制见 [D9B 数据审计](D9B_SOURCE_STATUS_20260923.md)和
[ISPRS 官方说明](https://www.isprs.org/resources/datasets/benchmarks/UrbanSemLab/2d-sem-label-vaihingen.aspx)。
