# D20 Vaihingen seed42 失败区域只读核查

## 已冻结的判断

seed42 的 P0、P1、P2 训练和 17 块 × 11 条件评价均已完成。P2 对最强对照 P0 的汇总增益为 +1.0261 pp，但 12、14 号块未过事先固定的逐块门槛。因此本轮开发筛选 **未通过**，不自动启动 seed17，也不因诊断结果删除失败块或调整门槛。结果见 [D20 报告](../experiments/D20_VAIHINGEN_SEED42_RESULTS_20260928.md)。

## 核查目的和范围

这次只读取服务器已有的 17 块开发区 TOP、DSM、FullGT，以及 P0/P2 的 clean 预测。12、14 号块为事后关注对象，其余 15 块提供同一批数据内的参照。脚本先核对原始输入与冻结清单的大小、SHA-256，再核对 clean 预测与归档摘要的 SHA-256；随后检查全像素标签颜色、TOP/DSM/标签尺寸、DSM 有限值和预测形状，并让 P2 独有正确／P0 独有正确的像素数回算到已归档的配对结果。

输出每块的光学通道均值与 0/255 比例、DSM 范围与分位数、各真值类别支持和配对得失、标签边界四像素邻域与内部的配对得失，以及建筑真值边界处的 DSM/光学梯度相对整图梯度之比。还记录 TIFF 空间标签的存在情况。它们只用于描述可能的输入或误差集中现象；边界梯度或数组同尺寸不能证明地理配准准确，也不能单独确定 P2 失分原因。

## 服务器执行

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
conda activate remote_sensing
git pull --ff-only origin rebuild-v1-protocol-20260915
bash scripts/run_rebuild_v1_d20_vaihingen_failure_inputs_audit.sh
cat records/rebuild_v1_d20_vaihingen_failure_inputs_20260928/tiles.tsv
```

脚本在 CPU 上前台运行，不启动训练，不占 GPU0/1，不读取 Potsdam Test6。全尺寸影像和预测要逐块重新哈希和解码，耗时以服务器实际输出为准。若完整报告已存在，启动器会拒绝覆盖；先检查既有结果。

服务器完整记录保存在 `records/rebuild_v1_d20_vaihingen_failure_inputs_20260928/`，包括 `source_audit.log`。适合跨电脑接力的状态、运行绑定、完整 JSON 指标和 TSV 另存于 `records/rebuild_v1_d20_vaihingen_failure_inputs_compact_20260928/`。不上传原始影像、预测或日志。

完成并检查 `audit.json` 的 `status=COMPLETE` 后，在服务器提交紧凑记录：

```bash
git add records/rebuild_v1_d20_vaihingen_failure_inputs_compact_20260928
git diff --cached --check
git commit -m "Archive D20 Vaihingen failure-input audit"
git pull --rebase origin rebuild-v1-protocol-20260915
git push origin rebuild-v1-protocol-20260915
```

这份诊断不改变 `decision.json` 的 `passed=false`。独立地域验证仍需解决 US3D/DFC2019 的数据传输与使用条件。
