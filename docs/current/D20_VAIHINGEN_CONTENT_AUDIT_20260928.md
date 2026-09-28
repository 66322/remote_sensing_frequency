# D20 Vaihingen 同域开发来源：内容检查入口

当前状态：**脚本已准备，服务器尚未执行；没有新训练或GPU队列。**
本检查使用服务器现有 Vaihingen 文件；US3D 仍是跨城市最终确认的优先来源。
旧审计已确认 17 个候选 ID 有提取文件和相同尺寸，但尚未检查完整标签的
实际像素值、光学通道和 DSM 有限数值。旧脚本还曾把去边界标签选成“完整标签”。

本轮明确选取同一数据根目录下的：

- `top/top_mosaic_09cm_area<ID>.tif`
- `dsm/dsm_09cm_matching_area<ID>.tif`
- `gts_complete/top_mosaic_09cm_area<ID>.tif`

若服务器实际目录不是这个布局，审计会列出各根目录的缺项，标记 `REVIEW_REQUIRED`，
由真实路径修正后再运行；不会用 `gts_complete_eroded/*_noBoundary.tif` 顶替。
每块读取影像核对尺寸、通道和 DSM 样本有限值；标签采样最多约10万像素，
统计已知颜色及未知颜色。标签采样通过不能证明全部像素合法；缺少可读地理
坐标时，只能确认像素尺寸相同，不能声称已证明空间对齐。

在服务器项目目录，先拉取本分支最新提交，然后运行：

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
将精简副本提交并推送到同一 GitHub 分支，另一台电脑才能看到实际判断。

通过的 ID 仅能用于**同一镶嵌图上的开发实验**。旧 F0/P1 已用部分场景，
其余场景与它们交错或邻近；没有独立最终确认集。Vaihingen TOP 通道为
近红外、红、绿；若随后做冻结 DINO 适配短流程，需单独冻结输入通道与
归一化方案，不能把结果称为 D20 US3D 的 RGB 跨地域复验。

历史来源与限制见 [D9B 数据审计](D9B_SOURCE_STATUS_20260923.md)和
[ISPRS 官方说明](https://www.isprs.org/resources/datasets/benchmarks/UrbanSemLab/2d-sem-label-vaihingen.aspx)。
