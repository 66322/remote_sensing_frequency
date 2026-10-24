# 混合退化 C0/C1 逐 tile 风险审计

## 目的

已完成的 E 组四项开发实验中，C1 相对 C0 的八个 pooled 条件均为正，但 Vaihingen 有局部下降。本审计复算原始逐 tile 6×6 整数混淆矩阵，定位 Potsdam `5_10`、Vaihingen `20` 和 `33` 的逐类 IoU、误报和漏报变化，并读取已有的边界与恢复诊断。它是对已有实验的解释，不新增训练、种子、数据下载或 test 评价。

## 输入与检查

从服务器读取原 E 队列 `queue_summary.json`、紧凑 `analysis.json`、四份正式训练 `summary.json` 和四份开发评价 `summary.json`。要求 E 队列和整数审计均为 4/4 完成、Test6 未加载、训练/评价签名与 checkpoint SHA 记录相符。脚本逐项复算有效像素、每类真值/预测/正确计数、每类 IoU、foreground-five mIoU，核对每个 pooled 矩阵等于 tile 矩阵之和，并核对已有的 pooled/逐 tile C1−C0 差值。不会重新读取 checkpoint 二进制或影像，也不运行预测。

输出写入 `records/post_d21_mixed_followup_compact_20260930/tile_risk_diagnostics.json`，包含源文件 SHA、各条件负迁移 tile 数、最差三 tile、指定 tile 的逐类变化、已有边界 F1 与恢复指标。边界计数来自 FullGT，仅 clean 条件有；恢复指标是有重叠推理窗口的像素加权诊断，不能当作独立样本。该审计不证明损失的因果机制，也不将同镶嵌图开发 tile 当作独立泛化证据。若输入与既有输出绑定不同，脚本报错而非覆盖结果。

## 资源与执行

仅使用 Python 标准库读取 JSON，预计数秒到数十秒、少量主机内存和磁盘；不占 GPU，不安装依赖。服务器在仓库根目录、`remote_sensing` 环境中逐条执行：

```bash
git pull --ff-only origin rebuild-v1-protocol-20260915
```

```bash
python -B scripts/analyze_rebuild_v1_mixed_tile_risk.py
```

若出现缺少评价摘要或绑定不符，先保存错误，不启动替代训练。完成后可只同步小型 JSON 到 GitHub，原始 checkpoint 和大预测仍留服务器。
