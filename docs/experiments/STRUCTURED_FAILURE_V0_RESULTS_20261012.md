# Structured Failure v0.1 结果验收（2026-10-12）

状态：**REVIEWED / PHASE1A_CLOSED / NO_SUPPORT_THIS_PROTOCOL / NO_FURTHER_DISPATCH**。

权威轻量原件提交：`fad186bece5170140f14f7b4e643ff3d102f1424`，目录：
`records/research_structured_failure_v0_20261012T073410_81887/evidence_20261012T164118006539_357012/`。

本次对上传后的 `summary.json` 进行独立 gzip-base64 精确解码并核对原始 SHA256：`dcbdc1e0bb19ba570bcc30e09c6ea2580abcafc9798c469c4faeb40966f5f20c`。42 个队列任务全部完成；固定统计汇总输出 `NO_SUPPORT_THIS_PROTOCOL`，没有自动扩样、Phase1B/Phase2 或新训练。

## 1. 冻结问题与统计量

范围为 Potsdam Val2 两张重复使用的 tile：`3_11`、`5_10`。四系统：RGB-only、S1-0、同 S1-0 权重的 `M000_masked`、同权重 `M000_context`；四类缺失掩码：pixel、random、gradient、matched；20 个事前固定 mask realization。

总量：640 个 missing inference cases + 8 个 clean cases + 6 个旧端点检查；optimizer updates = 0。

固定 damage 定义为缺失区域 NB fg5 mIoU 的百分点损伤：

`D = 100 × (mIoU_clean - mIoU_missing)`，越小越好。

主要统计量：

- `PE = D(gradient) - D(matched)`：结构/梯度位置效应，主模型固定为 S1。
- `CE = D(random) - D(pixel)`：块状几何相对像素缺失效应。
- `PE_total = D(gradient) - D(random)`。
- `CB = mIoU_context(missing) - mIoU_masked(missing)`：同权重 context 相对 masked 的缺失区收益；正值才表示 context 更好。

冻结开发门槛：S1 主 PE ≥ 0.30 pp、两张 tile 的平均 PE 均为正，并且 `PE_no_car ≥ 0.15 pp` 或 5 类中至少 4 类平均 PE 为正；若完整有效且主 PE < 0.15 pp，则固定判定 `NO_SUPPORT_THIS_PROTOCOL`。

置信区间为 5000 次 paired-mask bootstrap；统计范围条件于这两张重复 Val2 tile 和固定模型，不代表独立地域、训练 seed 或最终测试泛化。

## 2. 主判定：S1 的结构化 RGB 缺失脆弱性没有得到支持

| 项目 | 结果（pp） | 冻结判定要求 | 结果 |
|---|---:|---:|---|
| S1 主 PE | **+0.123**，95% CI **[-0.308, +0.593]** | ≥ +0.30 | 不满足；且 < +0.15，触发 NO_SUPPORT |
| tile `3_11` 平均 PE | **-0.062** | > 0 | 不满足 |
| tile `5_10` 平均 PE | **-0.083** | > 0 | 不满足 |
| S1 PE_no_car | **-0.553**，95% CI **[-0.906, -0.218]** | ≥ +0.15（或类别替代条件） | 不满足 |
| 五类 PE 均值 | **[-3.359, +1.618, +0.817, -1.287, +2.823]** | 至少 4/5 > 0 | 仅 3/5 为正 |

因此不是“刚好没过 0.30 pp”：**幅度、两 tile 符号一致性和类别支持三个条件均未建立**。固定 gate 的 `NO_SUPPORT_THIS_PROTOCOL` 是合理结论。

注意：主 PE 是每个 realization 先把两张 tile 的混淆矩阵池化再计算 mIoU 差，因此它不等于两个 tile 单独 PE 的算术平均；出现 pooled PE 为 +0.123 pp、两个 tile 的 realization 均值却略为负，并非计算错误。

## 3. 四系统的结构/几何效应

| 系统 | CE：random-pixel | PE：gradient-matched | PE_total：gradient-random | PE_no_car |
|---|---:|---:|---:|---:|
| RGB-only | **+2.939** [2.673, 3.212] | **+3.119** [2.831, 3.402] | **+3.325** [2.989, 3.657] | **+3.987** [3.694, 4.278] |
| S1 | +0.212 [-0.069, 0.500] | **+0.123** [-0.308, 0.593] | **-0.797** [-1.286, -0.283] | **-0.553** [-0.906, -0.218] |
| M000_masked | +0.951 [0.651, 1.260] | +0.929 [0.338, 1.553] | -0.606 [-1.157, -0.060] | -0.365 [-0.662, -0.057] |
| M000_context | **+5.157** [4.695, 5.611] | **+1.988** [1.434, 2.527] | **+2.243** [1.771, 2.672] | **+2.097** [1.804, 2.409] |

额外符号稳定性：RGB-only 的 PE 在 **20/20** 个 realization 中为正，CE 也是 **20/20** 为正；S1 的 PE 仅 **11/20** 为正。说明这套 mask 诊断并非“没有施加出结构差异”，而是这种明显的 RGB-only 结构敏感性没有在 S1 上保留下来。

S1 的 `PE_total = -0.797 pp` 且区间完全小于 0，说明在这个固定协议下，gradient 掩码反而比 random block 对 S1 的损伤略小；不能写成“S1 对高梯度结构缺失特别脆弱”。

## 4. 绝对缺失区 damage：S1 大幅削弱 RGB-only 的缺失损伤

下表为 20 realization 的平均 damage（pp，越小越好），每个 realization 均池化两张 tile：

| 系统 | pixel | random | gradient | matched |
|---|---:|---:|---:|---:|
| RGB-only | 56.111 | 59.050 | **62.375** | 59.256 |
| S1 | **21.652** | **21.864** | **21.067** | **20.945** |
| M000_masked | 25.091 | 26.043 | 25.436 | 24.507 |
| M000_context | 36.524 | 41.681 | 43.924 | 41.937 |

这里最值得保留的机制线索不是“Structured Failure 成立”，而是：**RGB-only 对结构化缺失确实很脆弱，而 S1 在固定权重下把缺失区 damage 从约 56–62 pp 压低到约 21 pp。** 这与 DSM/双模态融合在 RGB 退化时提供补偿的解释一致，但这里只能作为两张固定 Val2 tile 上的条件性证据，不能直接写成跨地域泛化结论。

## 5. 同权重 context 对照没有形成救援，反而明显更差

`CB = mIoU_context - mIoU_masked`，所以负值表示 context 版本更差：

| mask family | CB 均值（pp） | 95% CI |
|---|---:|---:|
| pixel | **-11.433** | [-11.608, -11.251] |
| random | **-15.638** | [-15.983, -15.296] |
| gradient | **-18.488** | [-18.855, -18.100] |
| matched | **-17.430** | [-17.935, -16.928] |

交互量：

- `I_placement = CB_gradient - CB_matched = -1.059 pp`，95% CI [-1.599, -0.528]。
- `I_geometry = CB_random - CB_pixel = -4.206 pp`，95% CI [-4.592, -3.820]。

因此 **M000_context 不能被描述成“利用上下文恢复缺失 RGB”成功**。在当前冻结权重、路由和输入定义下，它比 M000_masked 的缺失区 mIoU 稳定低 11–18 pp。更谨慎的解释是：这一特定 context 路径在缺失输入下可能发生明显的分布/路由失配；不能把它推广成“上下文本身无效”。

## 6. 科学结论

1. **关闭原主假设**：在固定 Structured Failure v0.1 协议下，没有证据支持“S1 的主要弱点是高梯度/结构位置 RGB 缺失”。
2. **诊断本身有效**：RGB-only 的 PE 为 +3.119 pp、20/20 realization 为正，说明 gradient vs matched 的结构差异确实能暴露单模态 RGB 的结构敏感性。
3. **双模态补偿是更强线索**：S1 把四类 mask 的绝对缺失损伤大幅压低，同时基本消除了 RGB-only 的结构位置效应。这更符合“DSM 对 RGB 缺失提供条件互补/鲁棒性”的研究主线。
4. **不要推进 naive context rescue**：M000_context 的绝对 damage 明显高于 M000_masked；当前实现不适合作为后续正向候选。
5. **不要因结果不支持而扩样追显著性**：不自动 20→40、不启动 Phase1B/Phase2、不追加 seed、不改 mask 定义、不启动新训练。

## 7. 限制与不可声称内容

- 只有重复使用的 Val2 `3_11`、`5_10`，不是独立地区。
- 20 个 mask realization 不是 20 个训练 seed，也不是 20 个独立场景。
- bootstrap 仅对 mask ID 成组重采样；不把像素视为独立重复，不报告未建立交换性假设的精确 p 值。
- matched mask 使用 GT 仅用于诊断匹配/评价，模型与路由不读取 GT；不能把它描述成部署方法。
- `test6_loaded=False`、`independent_final_loaded=False`；本轮不能写最终测试或跨数据集泛化结论。
- 大数组仍为 server-only；GitHub 保存轻量、可核验的整数统计、配置、代码、日志、manifest 和数组 SHA/index。

## 8. 当前研究决策

Structured Failure Phase1A 到此**技术与科学收口**。本结果不改变此前独立冻结的 Post-T F/H/R 候选与保护门槛；尤其不能因为本轮评价重新挑选训练 checkpoint。

下一步不是立即发新 GPU 队列，而是：

1. 独立完成已上传 Post-T paired v2 原件的科学验收；
2. 把其结果与本轮“RGB-only 强结构敏感、S1 显著削弱、context route 失败”合并，重新冻结下一研究问题；
3. 若继续模态可靠性主线，优先研究**可靠性/路由如何在模态退化时选择或抑制错误信息**，而不是继续证明已经被本协议否定的 S1 structured-location vulnerability；
4. 新实验必须另写冻结设计并显式登记；当前 **0 个自动后继任务**。

权威原件：`summary.json`、`summary.log`、`mask_manifest.json`、42 个 job receipts/logs，以及执行快照中的 `summarize_structured_v0.py` / `structured_v0_metrics.py`。