# Phase 1.5 — Recoverability Decomposition under Local RGB Failure

设计日期：2026-10-12（Asia/Shanghai）

状态：**EXECUTION_V1_2_READY_NOT_REGISTERED / ZERO_TRAINING / REAL_SMOKE_REQUIRED**。

落实说明：[执行协议](PHASE_1_5_EXECUTION_20261012.md)。用户2026-10-12“按上述规划进行”授权整套执行；技术smoke由控制器独立验收后自动接续全量，科学去留仍待完整原件人工复核。真实服务器smoke/登记尚未回报。

2026-10-12执行前澄清v1.1：[双卡24–48小时规划](PHASE_1_5_TWO_GPU_PLAN_20261012.md)。下文未展开的clean参考、oracle支持域、缓存/熵计费、ECI非正分母、统计解释与后继设计以该文件为准。此前版本37353e1可追溯；尚无本阶段新科学结果。用户授权GPU0/1、超过一天继续，当前不处理单卡释放。

本协议是 Structured Failure v0.1（Phase 1A）关闭后的唯一下一诊断阶段。Phase 1A 已按预注册规则判定 `NO_SUPPORT_THIS_PROTOCOL`；不得扩 realization、改阈值、换 mask 或追加 seed 追正。Post-T paired v2 也已完成验收；R−H 局部比较有正增量，但完整 E 条件保护 gate 失败。本阶段不把这些结果直接升级成新方法，而先回答一个更基础的问题：

> **S1 在 25% 局部 RGB missing 下仍有约 21 pp 的缺失区伤害，其中多少来自可恢复的模型/表示/融合不足，多少来自当前可见信息不足；现有专家之间是否存在足够且可学习的互补空间，值得重新打开 routing/reliability 主线？**

本阶段全部为冻结模型推理与离线统计，optimizer updates = 0。**任何 reliability estimator、side branch、adapter、retraining、额外 seed、Test6/held4/final 均不由本协议触发。**

---

## 1. 证据边界与冻结模型

开发数据仍仅使用 Potsdam Val2 两张重复开发 tile：`3_11`、`5_10`。native512/stride256、NoBoundary fg5 为主，Full/per-class/支持区统计为诊断。结论条件于这两张 Val2 tile 与现有冻结模型，不代表独立地区、训练 seed 或最终测试泛化。

冻结模型集合：

- **S1-0**：Phase 1.5 primary model。
- **R16**：用于1.5-A的冻结模型representation-depth对照及1.5-D的固定expert pool，不把其结果外推为S1-0机制。
- **S1-3**：仅进入 1.5-D oracle pool；其已知角色为“保留上下文 + 保留 fusion path”的旧开发候选。
- **RGB-only**：进入 1.5-D oracle pool，并作为 Phase 1A 的结构敏感 sanity anchor。
- **DSM-only**：优先使用仓库内可核验的冻结 checkpoint，但必须记录来源、训练 split、训练协议、backbone、seed 与 checkpoint SHA。

### DSM-only 兼容性限制

仓库现有 D15 DSM-only 来自较早的 Train16 / R01-era 16k 协议，和当前 S1/Post-T 的训练历史不匹配，因此默认标记为：

`LEGACY_DSM_ONLY / DESCRIPTIVE_ONLY_UNLESS_MATCHED_CONFIRMED`

它可以用于本阶段描述性 sufficiency/oracle 分析，但：

1. **如果 DSM-only 仍是 legacy checkpoint，则低 oracle headroom 不能单独作为关闭 routing 的充分依据**，因为弱 expert 会系统性低估可利用 DSM 信息。
2. 若 1.5-D 在 legacy DSM-only 下已经得到很高 headroom，则可作为更强的“至少存在互补空间”证据。
3. 若最终落入灰区或关闭区且结论高度依赖 DSM-only，允许在 Phase 1.5 结束后的独立设计评审中提出“matched DSM-only retraining”作为条件性后继；本协议本身仍保持 zero-training。

---

## 2. Phase 1.5-A — DSM content intervention

### 2.1 问题

在同一冻结模型内，S1 的结构位置敏感性消失是否依赖 DSM 的真实空间内容，而不是仅由双流容量、训练历史或 missing/OOD 状态造成？R16 是否表现出不同的 DSM 内容依赖方式？

### 2.2 模型

- primary：S1-0
- secondary representation-depth contrast：R16

两者分别解释，不预设结果一致。

### 2.3 RGB mask

完全复用 Structured Failure v0.1 的 20 个事前固定 realization、两 tile、四 mask family：

- pixel
- random
- gradient
- matched

不得重新采样或后验挑 realization。

### 2.4 DSM 条件

固定四档：

1. **intact**：原 DSM。
2. **crop-shuffle**：先在完整 tile 上按固定 512×512 非重叠网格切块，块内像素与局部结构保持不变，仅对 512 块的位置做事前固定的无放回置换；用于破坏长程/区域级空间对应，同时尽量保留块内局部纹理统计。边缘不足512的块按相同(h,w)形状分组置换，不padding再裁切；6000边长余368。原tile严格双射，保存固定点比例。
3. **tile-shuffle**：在完整 tile 内使用事前固定的全像素双射 permutation，保持 DSM 像素值多重集合不变，但破坏局部与全局空间结构。保存 permutation seed/index SHA；输出必须由原 DSM 纯索引重排得到，不做插值。
4. **zero**：严格复用当前仓库已有 robustness evaluator 的 DSM-zero 定义与输入阶段，不创建新的 zero 语义；用于“完全缺失/OOD”参照，不与 shuffle 视为对称干预。

crop-shuffle 与 tile-shuffle 的随机映射只由协议、tile、condition 决定，不随 RGB mask realization 改变，避免把 DSM 随机性混进 mask bootstrap。

### 2.5 指标

沿用 Phase 1A：

`D_j(M) = 100 × [mIoU(clean RGB, DSM_j; M∩NB) - mIoU(masked RGB, DSM_j; M∩NB)]`

同DSM干预j的clean参考与RGB缺失条件配对；相对intact clean的总损伤另报，不混入主RGB缺失效应。

主结构统计：

`PE = D(gradient) - D(matched)`

辅助：

`PE_total = D(gradient) - D(random)`

对每个模型报告：

- `PE_intact / PE_crop_shuffle / PE_tile_shuffle / PE_zero`
- `ΔPE_crop = PE_crop_shuffle - PE_intact`
- `ΔPE_tile = PE_tile_shuffle - PE_intact`
- `ΔPE_zero = PE_zero - PE_intact`
- 四族 absolute damage
- 五类 per-class effect
- 两 tile 分开方向

统计以 20 个 paired realization 的效应量为主；5000 次 paired-realization bootstrap CI 为主区间。exact paired sign-flip permutation 仅作为次要检验，并明确依赖 paired difference 对称/交换假设，不以单个 p 值替代效应量。

### 2.6 预注册解释

- `PE_intact ≈ 0` 且 `PE_crop_shuffle > PE_intact`：支持 DSM-RGB 空间对应关系参与抑制结构位置敏感性。
- `PE_crop_shuffle ≈ PE_tile_shuffle > PE_intact`：支持 DSM 空间内容/对应被破坏后结构敏感性恢复；不进一步声称具体尺度机制。
- 只有 zero 明显改变 PE，而两种 shuffle 不改变：更符合 missing/OOD 状态效应，而不是“真实空间对应”为唯一机制。
- S1-0 与 R16 若响应不同，只能写成 frozen-model representation-depth association；不得直接归因于“最后 4 block 因果决定 DSM 利用方式”。

任何结果都不自动触发训练。

---

## 3. Phase 1.5-B — Ratio response / saturation diagnostic

### 3.1 问题

25% local RGB missing 是否已经进入补偿饱和区，从而把位置差异淹没？

### 3.2 模型与 mask

仅 S1-0。

**ratio sweep 只使用 pixel-level mask**，不使用 block family，避免 missing ratio 与 effective block size 同时变化。

对每个固定 realization 构造严格 nested mask：

`M5 ⊂ M10 ⊂ M25`

ratios：5% / 10% / 25%，20 realization × 两 tile。

`M25` 必须与 Phase 1A 对应 pixel realization 的 25% mask canonical SHA 一致；`M5/M10` 由事前固定像素排序截断得到，不重新抽样。

### 3.3 指标

报告：

- `D(r)`
- `PE(r)=NA`：pixel-only没有gradient/matched配对，不能计算该PE。分别报告整图D_NB、缺失区D_M与公共M5支持上的D_core；主要看corruption dose-response。
- support-level error increment：`ΔErr_mask(r) / |M_r|`
- `D(r)/r` 作为**剂量归一化 mIoU 效应**，仅为启发式，不称“每像素伤害”，因为 mIoU 对像素并非线性。

主要 saturation 证据来自：

1. 随 r 增大，`ΔErr_mask(r) / |M_r|` 是否递减；
2. `D(r)` 是否明显次线性增长；
3. 与 1.5-E 的空间 profile 是否同时显示大缺失区内部进入 plateau。

### 3.4 smoke 与统计功效

**1 个 realization 只用于 smoke/known-answer，不用于估计 realization 方差或最小可检测效应。** 一个 realization 无法估计跨-realization 方差。

正式科学结论固定使用 20 realization。若 5% 档因分母太小/类别支持不足导致某些 per-class 指标不稳定，标记 `INCONCLUSIVE_LOW_SUPPORT`，不得在看完结果后删掉 5% 档或用新增 realization 补功效。

---

## 4. Phase 1.5-C — Per-class recoverability decomposition

### 4.1 问题

剩余伤害是否呈现明显类别依赖，特别是 RGB 纹理主导的 Car 与 DSM 几何更有利的 Building 是否不同？

### 4.2 模型

primary：S1-0。

DSM-only 只作为 sufficiency reference，并按第 1 节的 checkpoint 兼容性等级解释。

### 4.3 输出

五个 fg 类全部报告；事前 primary contrast：

`Car - Building`

对每个 tile × realization × condition 持久化：

- int64 6×6 confusion matrix
- per-class valid/support pixel count
- per-class IoU
- per-class recall
- clean→corrupted 新增错误数
- corrupted→clean 恢复数（如适用）

不得只保存最终均值。所有 per-realization per-class confusion matrix 必须进入轻量上传原件，保证后续 post-hoc 混淆分析无需重新 GPU 推理。

### 4.4 解释限制

DSM-only 在某类表现较强/较弱只能说明**当前 frozen expert 下的可用信息参照**，不是 Bayes/info-theoretic upper bound。尤其 legacy DSM-only 不允许用于声称“该类信息原则上不可恢复”。

---

## 5. Phase 1.5-D — Oracle headroom and routing learnability

这是决定 reliability/routing 是否重新获得入场资格的关键诊断。

### 5.1 Oracle pool

事前冻结五 expert pool：

`{S1-0, S1-3, DSM-only, RGB-only, R16}`

每个 expert 必须在**完全相同的 tile、RGB corruption mask、DSM condition、NB mask 与评价支持**上生成预测。若某 expert 因协议/输入不兼容无法合法评价，该 expert 标记 `UNAVAILABLE`，不得用替代 checkpoint 临时补位；pool 缩减必须在结果解释中显式记录。

### 5.2 Known-mask selector

raw composition：

- mask 外：S1-0 prediction
- mask 内：DSM-only prediction

这是“已知 failure support 时，简单 expert substitution 能否恢复”的诊断，不代表部署 router。

#### 边界伪影处理

**raw composition 是主结果，也是 gate 使用结果。**

另报一个 seam-smoothed secondary：只允许在 composition seam 的 1-pixel 邻域内做固定 3×3 majority/mode filter；seam 外预测必须 bitwise 不变。若 3×3 平票，回退 raw label。不得对整幅图做平滑。

报告：

`BoundaryArtifactSensitivity = Score(smoothed) - Score(raw)`

这只衡量 composition 对 seam 后处理的敏感性，不用 smoothed 数字覆盖 raw gate，也不把 majority filter 当方法贡献。额外单列 Car，防止 mode filter 对小目标的系统性伤害被 pooled 指标掩盖。

### 5.3 GT expert oracle

GT 只用于离线诊断选择，不进入模型或部署路径。

#### per-pixel oracle

每个 NB valid pixel：若 pool 中至少一个 expert 预测正确，oracle 输出一个正确标签；若多个 expert 正确，按固定优先级

`S1-0 > S1-3 > R16 > DSM-only > RGB-only`

打破 tie（正确标签本身相同，优先级只用于可追踪来源）；若无 expert 正确，回退 S1-0 预测。

计算：

`H_oracle_pixel = Score(Oracle_pixel) - Score(S1-0)`

#### per-patch oracle

固定 patch 粒度：128、256，top-left 网格锚定；边缘不足 patch 的区域保留实际范围，不重叠补窗。

每个 patch 用 GT 选择**单一 expert**，目标为该 patch NB valid pixels 上 correct-count 最大；tie 使用上述固定优先级。然后将 patch 预测拼成完整图，统一计算 pooled mIoU。

报告：

- `H_oracle_patch128`
- `H_oracle_patch256`
- expert selection histogram
- 每 tile / 每类来源比例

per-pixel any-correct是固定专家池正确率上界及乐观mIoU诊断，不是全局最优mIoU上界；per-patch优化correct-count也不是直接优化mIoU。主gate在完整NB fg5上、先按realization池化两tile再计算、四族均值；缺失区/healthy区另报，2/6pp不可挪到缺失区。另报超过最佳固定专家的空间。

### 5.4 条件胜率 / learnability analysis

只在 experts **预测不一致**的像素上分析 expert correctness。

分成两类，严禁混用：

#### A. mechanism-only diagnostic bins（不能作为部署可学习性证据）

- GT class
- 到真实 synthetic mask 边界的距离
- 真实 mask connected-component size

这些变量可解释专家互补结构，但 GT/真实 failure mask 在一般部署中未必可得，因此**不能单独让 reliability route 通过 learnability gate**。

#### B. deployment-observable bins（可用于 learnability 评审）

固定从推理时可获得量构造，不读取 GT：

- local DSM mean / variance / gradient-magnitude bins
- local RGB observed-zero fraction（仅适用于本 synthetic missing 协议，必须标注不能外推到 blur/shift）
- S1-0 predictive entropy bins
- expert agreement count / S1-vs-DSM-only disagreement indicator

bin 边界必须在正式统计前固定在代码/manifest 中；优先使用事前固定等宽或基于 clean reference 的 quantile，不允许看 correctness 后调 bin。

对每个 bin 报告：

`P(expert_i correct | bin)`、support count、两 tile 分开结果、expert win margin。

本阶段**不预设一个新的数值 learnability 通过阈值**，避免再次后验调 gate。`H_oracle ≥ 6 pp` 只提供 conditional entry；只有当 deployment-observable 条件下存在跨 tile 可重复的专家偏好结构时，才允许进入下一次独立设计评审。若高 oracle 仅由 GT class/真实 mask geometry 才能解释，则 routing 仍不得自动启动。

### 5.5 Headroom gate

基于 **raw per-pixel 5-expert oracle**：

- `< 2 pp`：routing/reliability 默认关闭；但若 DSM-only 为 legacy 且结果对其敏感，只能记为 `PROVISIONAL_CLOSE_DSM_EXPERT_LIMITED`，不能永久关闭。
- `2–6 pp`：gray zone；优先与 representation/context side-branch 的可预期收益比较，不自动训练 router。
- `≥ 6 pp`：仅获得 `CONDITIONAL_ENTRY`；仍必须通过上一节 deployment-observable 条件胜率的可学习性评审，且不得自动派发 estimator 训练。

6 pp 不是成功判定，而是“值得继续设计”的最低入场券。

---

## 6. Phase 1.5-E — Spatial damage profile

这是本阶段优先执行、成本最低的空间诊断。

### 6.1 问题

S1-0 在局部 RGB missing 下的剩余伤害主要集中于 mask 边界，还是在 mask 内部近似均匀？

### 6.2 范围

模型：S1-0。

使用 Phase 1A 已存在的 25% block-like mask family：

- random
- gradient
- matched

pixel family 不进入 distance-profile 主分析，因为孤立像素缺乏可解释的内部距离层级。

20 realization × 两 tile，直接复用已有 mask 与尽可能复用已有预测；若已有预测足以计算，不重复 GPU 推理。

### 6.3 距离与分箱

在每个 mask 连通区域内部计算到该 mask 边界的 Euclidean distance transform。

固定 bins：

- `[0, 4)` px
- `[4, 16)` px
- `[16, 64)` px
- `>= 64` px

每 bin 保存 valid pixel count，低支持 bin 不与高支持 bin等权平均。

### 6.4 两种 damage 定义

同时报告，避免 clean 预先错误混入：

1. **GT error damage**：corrupted 相对 GT 的 error rate，并减去同位置 clean error rate。
2. **clean→corrupted flip rate**：clean 正确、corrupted 变错的像素比例；另报 clean 错→corrupted 对的 recovery rate。

每个 bin、每类、每 tile、每 realization 均保存计数。

### 6.5 空间形态判定

定义 pooled edge concentration index：

`ECI = damage_density_[0,4) / damage_density_[16,∞)`

其中 denominator 将 `[16,64)` 与 `>=64` 按像素数池化；若内部支持不足则记 `INCONCLUSIVE_INTERIOR_SUPPORT`。净damage分母≤0或bootstrap分母非正时记INCONCLUSIVE，不加epsilon制造ECI；另报新错密度比。

预注册解释：

- **edge-dominant**：两 tile 的 ECI 均 > 1，pooled ECI ≥ 1.5，且 paired-realization bootstrap 95% CI 下界 > 1。
- **approximately uniform**：pooled ECI ∈ [0.8, 1.25]，两 tile 无稳定单调距离衰减，且区间不支持 ≥1.5 的 edge concentration。
- 其他：`MIXED_OR_INCONCLUSIVE`。

该分类只决定 Phase 2 设计的空间 footprint 假设，不证明 receptive field 是唯一原因。

---

## 7. Smoke / known-answer gate

正式全量前只运行 **1 个冻结 realization** 做工程 smoke；默认 `realization_id=1`、tile=`3_11`。smoke 不用于科学效应估计、方差估计、模型选择或阈值修改。

必须全部通过以下 known-answer tests：

1. **Archived replay**：S1-0 + intact DSM + Phase1A 25% 原 mask 的关键矩阵/指标与已上传 Phase1A 原件一致（整数 confusion matrix 要求 exact；浮点派生指标由 exact matrix 复算）。
2. **Mask identity**：1.5-B 的 `M25` canonical SHA 与对应 Phase1A pixel mask 完全一致。
3. **Nested identity**：逐像素验证 `M5 ⊂ M10 ⊂ M25`，并验证精确像素数。
4. **Shuffle bijection**：crop-shuffle/tile-shuffle 的 index map 为双射；输出只由原 DSM gather 得到，无插值；manifest 保存 permutation SHA。
5. **Distance-transform toy test**：对程序内固定小矩形/环形 toy mask，distance bins 与手算 expected counts 完全一致。
6. **Oracle toy test**：固定 4×4 toy GT + 5 expert predictions，per-pixel oracle、128/256 逻辑对应的小尺度 toy patch oracle、tie-break 与 expected correct counts 完全一致。
7. **Composition identity**：raw known-mask selector 在 mask 外 bitwise 等于 S1-0，在 mask 内 bitwise 等于 DSM-only。
8. **Seam smoothing containment**：smoothed 与 raw 的差异只能出现在事前定义的 1-pixel seam band；seam 外 bitwise identical。
9. **Confusion conservation**：每个矩阵元素和等于该评价支持上的 NB valid pixel 数；per-class support 与矩阵行和一致。
10. **Zero-training protection**：无 optimizer 构造/step、无 backward、无 checkpoint 写回；记录 `optimizer_updates=0`。
11. **Data isolation**：`test6_loaded=false`、`held4_loaded=false`、`independent_final_loaded=false`。
12. **Checkpoint binding**：五 expert 的配置、checkpoint SHA、来源记录、预处理签名全部写入 manifest；任何绑定不明即 HOLD。

只要一项 FAIL：状态改为 `SMOKE_FAILED_HOLD`，不得边跑全量边修；修复后必须版本化协议/代码并重新 smoke。smoke PASS 只代表工程管线可运行，不代表科学假设通过。

---

## 8. 执行顺序与资源规则

固定执行顺序：

1. **1.5-E**：优先复用 Phase1A 预测做空间 profile；能离线复算则不占 GPU。
2. **1.5-A**：S1-0 + R16 DSM intervention。
3. **1.5-B**：S1-0 5/10/25% pixel nested dose-response。
4. **1.5-C**：per-class sufficiency decomposition。
5. **1.5-D**：统一收集 5-expert predictions 后计算 raw composition、oracle 与条件胜率。

不因中间结果提前停掉已经冻结的其他诊断；五项一起回答 A/B/C/可学习性问题，避免 sequential cherry-picking。

资源上仅允许推理与离线 CPU 统计。smoke 后记录每 case 实际 GPU 秒、峰值显存与预测缓存大小，用于调度；**不在协议里承诺 `<2 GPU·hour`**。若按 smoke 实测外推资源异常大，只允许 HOLD 设计评审，不允许通过删 condition/realization 来适配预算。

---

## 9. Phase 1.5 结束后的唯一决策树

### Branch C / low recoverability

如果：

- oracle headroom 小，或
- legacy DSM-only 限制消除后仍小，或
- 高 oracle 仅在 GT/真实 mask 条件下可解释，deployment-observable 条件没有可重复 expert preference，

则 reliability/routing 主线关闭或保持灰区。优先进入 **capability-preserving residual context adaptation** 的独立设计评审。

若 1.5-E 为 edge-dominant，则后续 correction footprint 优先聚焦 boundary band；若 approximately uniform，则不得把“扩 receptive field / 边界修复”当默认解释。

### Branch R / conditional routing entry

如果 raw 5-expert `H_oracle_pixel ≥ 6 pp`，且 deployment-observable 条件胜率出现跨两 tile 可重复的专家偏好结构，则 reliability/routing 获得 `CONDITIONAL_ENTRY`。下一步仍需先写独立 oracle-conditioned 设计与 capacity-matched control，不直接复活 E50/D9/D10/D11/D12/D23/D27/B4 的已关闭配方。

### Representation-depth implication

Post-T 的 R−H 正增量只作为后续 side-branch 深度参考：若进入 adaptation 路线，优先考虑**冻结 anchor + zero-init residual late-encoder/interface adapter**，而不是直接开放最后 4 block。未来训练必须混合 clean + failure，并显式保持 healthy-path protection；本协议不实现该训练。

---

## 10. Registry findings to preserve

本协议执行前/后应保持以下 finding 相互独立，不混成单一故事：

1. **F-RGB-STRUCT**：RGB-only 在 Phase1A 中有稳定结构位置敏感性；`PE=+3.119 pp`，20/20 realization 同向。
2. **F-S1-STRUCT**：S1 structured-location vulnerability 未获支持；Phase1A 正式关闭。
3. **F-S1-FLAT**：S1 四 mask family 的 absolute missing-region damage 约 21 pp，机制仍 open；**Phase1.5 结束前不得作为论文确定机制引用。**
4. **F-CONTEXT-TOPOLOGY**：S1-3 的 preserved/residual context path 与 M000 replacement-style context route 不是同一机制，不能互相外推。
5. **F-POSTT-DEPTH**：R−H 局部比较通过，但 full E protection gate 失败；只能作为 representation-depth 线索。
6. **F-CONTEXT-TOPOLOGY-QUANT**：固定量化：S1-3 vs S1-0 RGB_U `+4.102 pp`（两 tile约 `+4.151/+4.077`）；M000_context vs M000_masked 在 pixel/random/gradient/matched 分别约 `-11.433/-15.638/-18.488/-17.430 pp`。

这些 finding 的 registry 写入属于记录整理，不改变任何科学 gate。

---

## 11. 不允许的动作

Phase 1.5 完成与独立验收前：

- 不训练 reliability estimator。
- 不训练 α/β/γ soft gate。
- 不新增 side branch / adapter。
- 不重训 matched DSM-only；仅允许把它列为 Phase1.5 后的条件性后继。
- 不增加 Phase1A realization。
- 不修改 Structured Failure 的 stop rule。
- 不用 smoothed composition 代替 raw oracle gate。
- 不用 GT class / true mask geometry 作为“部署可学习性”证明。
- 不把 DSM-only 称为 information-theoretic upper bound。
- 不访问 Test6 / held4 / final。
- 不因某个中间结果漂亮而跳过其余冻结诊断。

---

## 12. 当前执行状态

截至本次落实：**执行包已实现并通过20项合成CPU检查/13新Python语法；READY_NOT_REGISTERED，无服务器真实smoke或登记回报。**

下一步只能是：

1. 用户运行固定commit的enqueue_phase15.py，幂等核旧队列与锁；
2. 控制器运行同包CPU检查/准备及ID1真实smoke，并在GPU1复验同case；
3. 独立技术验收smoke receipt全PASS后自动接续全量推理，任何FAIL即HOLD；
4. 全量完成/HOLD后前台轻量上传原件；助手回读并做科学验收，不自动派发新训练。

在此之前状态保持：

`PHASE_1_5_EXECUTION_READY_NOT_REGISTERED`
