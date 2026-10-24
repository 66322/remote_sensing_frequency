# D20 Vaihingen seed42 失败区域输入核查结果

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: result interpretation
- Origin Date: 2026-09-28
- Verification Status: SERVER_COMPLETE; HASH_BOUND; DESCRIPTIVE_ONLY
- Version Label: v1

服务器在 `43dbbe3` 于 2026-09-28 18:04:20–18:04:42 +08:00 完成 CPU 只读核查，退出码 0；紧凑证据归档于 `21dbb2d`。17/17 个开发块的原始 TOP、DSM、FullGT 均与冻结输入清单的大小和 SHA-256 一致；P0/P2 的 clean 预测均与已归档评价摘要的 SHA-256 一致。完整标签调色板、尺寸和 DSM 有限值检查通过；逐块配对纠错／改错计数与原 `decision.json` 完全一致。总计 90,200,065 个开发区像素。本机对照 Git 原始 blob 核实了审计源码、配置、决策、输入清单的哈希；Windows 工作副本的部分 JSON 为 CRLF 换行，不用于与服务器 LF 文件直接比对 SHA。

证据：[完整 JSON](../../records/rebuild_v1_d20_vaihingen_failure_inputs_compact_20260928/audit.json)、[逐块 TSV](../../records/rebuild_v1_d20_vaihingen_failure_inputs_compact_20260928/tiles.tsv)、[状态](../../records/rebuild_v1_d20_vaihingen_failure_inputs_compact_20260928/status.tsv)、[运行绑定](../../records/rebuild_v1_d20_vaihingen_failure_inputs_compact_20260928/run_context.txt)。

## 12、14 号块的得失

| 区域 | P2 独有正确 | P0 独有正确 | 净正确像素 | 标签边界 4 px 内净值 | 内部净值 | clean mIoU_fg5 差值 |
|---|---:|---:|---:|---:|---:|---:|
| 12 | 122,921 | 155,011 | −32,090 | −1,057 | −31,033 | −0.7655 pp |
| 14 | 124,645 | 112,557 | +12,088 | +1,456 | +10,632 | −0.3743 pp |

12 号块的负净值主要发生在内部，而非只集中于标签边界。按真值类别分解，Tree 净少判对 37,415 像素，Building 净少 11,606，Impervious 净少 4,749；LowVegetation 净多判对 21,920。该模式与类别混淆有关，但不能从这张表确定模型为什么改变预测。

14 号块虽然总体正确像素增加，Car 的 clean IoU 仍从 P0 的 48.4712% 降到 P2 的 45.2948%。Car 真值仅 13,160 / 4,922,235 像素；混淆矩阵显示 Car 真阳性从 10,019 增到 10,079，同时 Car 假阳性从 7,510 增到 9,092（+1,582）。因此 Car 的交并比下降与总体像素正确数增加可以同时发生；这也是五类等权 mIoU 与 OA 不同方向的直接计数解释。它不构成放宽逐块门槛的理由。

## 输入异常证据边界

12、14 号块 DSM 在建筑真值边界的梯度相对全图梯度分别为 2.570、2.601；17 块范围为 2.386–5.509。光学梯度比为 2.536、2.661；17 块范围为 1.873–3.255。两块 TOP 三通道的 0/255 饱和比例较低，DSM 全像素有限且数值范围落在本批其他块的总体范围内。核查未发现文件损坏、未知标签色、尺寸不符或这些描述统计所能识别的突出异常。

17 块 TOP/DSM/标签 TIFF 均没有脚本检查的 GeoTIFF 空间标签。尺寸相同和边界梯度增强**不能证明地理配准准确**；这次核查也未量化残余位移。12/14 号块是根据失败结果事后选出的诊断对象，所有观察只用于解释，不作为重新选择区域或修改门槛的依据。

## 冻结决定与下一阶段

原 D20 Vaihingen seed42 开发判断仍为 `passed=false`：P2 汇总增益 +1.0261 pp，但 12/14 号块违反预设逐块门槛。不补 seed17，不重跑相同三组，不剔除区域，不改变阈值。Vaihingen 与旧实验同属镶嵌图，仍只是同域开发证据。

独立地域验证的下一阻塞是 US3D/DFC2019 Track 1 的数据取得、传输方式与使用条件。现有来源记录表明服务器对 GRSS/DataPort 的代理请求返回 403，官方 torrent 元数据可达，而原始数据尚未落盘。先核实官方获取及使用许可，尤其是任何第三方中转是否获准；在此之前不上传受限原始包、不启动新 GPU 队列。若 US3D 最终不可用，按已有 D20 协议对 Houston 做一次来源准入检查。
