# 下一阶段实验执行规划

**项目：** RGB–DSM 多模态遥感语义分割  
**当前阶段：** Structured Partial Modality Failure / Context-Preserving Local Adaptation 问题确认  
**当前目标：** 在不干扰正在进行的 F/H/R × 8k/16k 实验的情况下，并行完成 Phase 1 evaluation-only 实验，回答“连续性效应、内容位置效应、上下文补偿效应”三个核心问题。

---

# 0. 执行前必须先检查仓库

首先读取当前仓库最新状态，不允许直接依据聊天中的旧状态启动任务。

必须优先阅读：

- `docs/START_HERE.md`
- `docs/current/PROJECT_STATUS.md`
- `docs/current/RESEARCH_DECISION.md`
- `docs/current/NEXT_EXPERIMENT.md`
- `docs/experiments/POST_N3_S1_RESULTS_20261008.md`
- `docs/experiments/POST_S1_FULL_TRANSFER_PARTIAL_RESULTS_20261010.md`
- `docs/experiments/POST_T_FULL_RESULTS_20261011.md`
- `docs/experiments/POST_T_MECHANISM_RESULTS_20261011.md`
- `docs/protocols/POST_T_PAIRED_V2_EXECUTION_20261011.md`
- `records/rebuild_v1_experiment_registry.json`

当前活动分支以：

`rebuild-v1-protocol-20260915`

为基准，但必须重新查询最新 HEAD。

## 不可违反的约束

1. 不得修改、打断、重复登记、重启当前 F/H/R × 8k/16k 实验。
2. Phase 1 不新增训练。
3. 不读取 Test6。
4. 不使用 held-out/final 数据做开发决策。
5. 不修改历史 D1–T 实验。
6. 不重新开启已经关闭的 frequency、semantic prototype、D27 router、N2 relation、N3 region assignment、N5 content-aware training、D30 recover sweep。
7. 当前阶段只允许：
   - 读取已有 checkpoint；
   - 生成 evaluation masks；
   - 推理；
   - 统计分析；
   - 生成 protocol / registry / evidence。
8. 如果 GPU0/GPU1 仍被 Phase 0 使用，先完成 CPU 侧协议、mask 生成器、registry、smoke test，不得抢卡。

---

# 1. 本阶段只回答三个科学问题

## Q1：连续性效应 Continuity Effect

问题：

> 在总 missing ratio 完全相同时，连续块状局部缺失是否比随机散布缺失更加有害？

定义：

\[
CE=D(U_{block})-D(U_{pixel})
\]

其中：

- `U-pixel`：随机散布缺失；
- `U-block`：连续 block 缺失。

如果：

\[
CE>0
\]

说明 failure footprint 的连续性本身会放大伤害。

---

## Q2：内容位置效应 Content-location Effect

问题：

> 在 failure footprint 几何形状、面积、类别构成尽量相同的情况下，把缺失放到高 DSM 结构变化区域，是否仍然比随机位置更危险？

主终点：

\[
\Delta^*=D(S_{grad})-D(U_{block}^{matched})
\]

这里必须保证：

`S-grad` 与其 twin `U-block`：

- primitive 数量相同；
- primitive shape 相同；
- block size 相同；
- missing ratio 相同；
- 尽可能匹配 semantic composition；
- 唯一主要区别是 placement。

因此这个量才可以解释为：

> content-dependent placement effect。

---

## Q3：上下文补偿效应 Context Mediation

使用已有：

- `S1-0`：masked-context / hard fallback；
- `S1-3`：context-preserving / retained fusion。

定义：

\[
CB(M)=Perf_{S1-3}(M)-Perf_{S1-0}(M)
\]

重点计算：

- `CB(U-pixel)`
- `CB(U-block)`
- `CB(S-grad)`
- `CB(S-boundary)`

核心假设：

> failure 越连续、越结构化，对区域外上下文依赖越强，因此 context-preserving 的收益应更大。

---

# 2. 第一轮模型集

第一轮只允许使用已有模型，不训练。

## M1：RGB-only anchor

使用当前协议中的真正 Optical/RGB-only 强基线。

必须明确：

- experiment id；
- checkpoint SHA；
- selected step；
- config；
- model role。

注意不要混淆：

- REBUILD 的 `R01`
- Post-S1 中名为 `R0` 的强 spatial-composition control。

这两个不是同一个模型。

---

## M2：Dual anchor

使用当前强普通 RGB+DSM 融合基线。

必须明确 checkpoint 来源。

---

## M3：S1-0

masked-context / hard fallback。

---

## M4：S1-3

context-preserving / retained fusion。

---

## 后续模型

F/H/R × 8k/16k 完成并按原协议独立验收后，最多追加：

> 其事前规则允许保留的 representative / winner。

不得因为 Phase 1 的结果反向选择最有利 F/H/R 组。

QD robust、Post-S1 R0 等作为第二批扩展，不属于第一轮必须项。

---

# 3. 第一轮 Failure Protocol

第一轮只研究：

> **RGB local missing，25% missing ratio。**

Primary corruption：

> RGB zero-fill。

暂时不扩展：

- DSM missing；
- 50%；
- 75%；
- noise；
- blur；
- shift；
- seam；
- DSM mean-fill；
- mask detection training。

---

# 4. Mask family

## 4.1 U-pixel

作用：

标准 Random Missing 参考。

要求：

- missing ratio = 25%；
- 20 fixed seeds；
- 在完整 6000×6000 tile 坐标上先生成 mask；
- sliding inference 时复用同一整图 mask；
- 禁止在每个 512 crop 内独立随机。

---

## 4.2 U-block

作用：

测量 continuity effect。

每个 seed 先产生一套固定的 failure primitives，例如：

- 64×64；
- 128×128；
- 256×256；

或第一轮先统一 128×128。

要求：

- 总面积约 25%；
- primitive 列表在 seed 创建时固定；
- 对应 S-grad twin 复用完全相同 primitive。

---

## 4.3 S-grad

作用：

测试 content-dependent placement。

### Gradient 定义

冻结：

- gradient operator；
- normalization；
- percentile q；
- scoring method。

建议：

> Sobel DSM gradient + domain 内 top-q percentile。

Potsdam 和 Vaihingen 冻结的是：

> q 和规则，

不是绝对 gradient 数值。

---

## S-grad 的关键约束

不能直接：

> threshold high-gradient pixels → 得到一堆细碎像素 → 当 structured mask。

正确方法：

先固定 primitive：

```text
block A
block B
block C
...
```

然后：

- U-block：随机放这些 block；
- S-grad：根据 block 覆盖区域的 DSM-gradient score 选择位置。

因此同一个 seed：

`S-grad-017`

和：

`U-block-017`

必须具有：

- 完全相同 block size；
- 完全相同 block count；
- 完全相同总面积；
- 只有 placement 不同。

---

## 4.4 S-boundary

作用：

诊断 semantic/object boundary 是否也形成 structured vulnerability。

规则：

- 使用 GT semantic boundary；
- 仍使用与 U-block 相同 primitives；
- 按 boundary occupancy / score 选择位置。

注意：

> S-boundary aware 只能标记为 diagnostic-only。

因为真实推理阶段不能获得 GT semantic boundary。

禁止把 GT boundary mask 当正式部署输入。

---

# 5. Geometry × Placement 分解

第一轮至少形成：

|  | 随机位置 | 内容相关位置 |
|---|---|---|
| 散布/随机 | U-pixel | 暂不做 |
| 连续 matched footprint | U-block | S-grad / S-boundary |

因此可以分别估计：

## Continuity Effect

\[
CE=D(U_{block})-D(U_{pixel})
\]

## Placement Effect

\[
PE=D(S_{grad})-D(U_{block})
\]

后者才是：

> structured/content-dependent missing

的主要证据。

---

# 6. Mask paired design

每个 structured seed 创建时必须同步生成 matched random twin。

例如：

```text
seed 001:
S-grad-001
U-block-001

seed 002:
S-grad-002
U-block-002
```

第一轮固定：

> 20 paired seeds。

如果主效应处于 borderline zone，只允许按照预注册规则扩到：

> total 40 seeds。

不允许临时决定继续采样。

---

# 7. Mask Registry

每个 mask 保存：

- `mask.npy`
- `mask.png`
- `config.json`
- `metadata.json`

科学绑定使用：

> canonical `mask.npy` array bytes 的 SHA256。

PNG 仅用于可视化。

---

## metadata 至少记录

- dataset
- tile
- seed
- family
- paired_twin_id
- missing_ratio
- corruption_operator
- primitive_sizes
- primitive_count
- placement_rule
- gradient_operator
- gradient_quantile
- semantic_histogram
- boundary_fraction
- mask_pixel_count
- canonical_mask_sha256
- generator_commit
- protocol_version

---

# 8. Known-answer Smoke Test

鉴于历史上出现过 D24 scientifically-invalid ablation，本阶段正式评价前必须先验证 evaluator。

构造 synthetic case：

- 人工 GT；
- 人工 prediction；
- 固定 mask；
- 在 mask 内强制翻转已知数量的正确像素；
- mask 外完全不变。

必须可以人工算出：

- confusion matrix；
- `D(M)`；
- whole score；
- healthy flip；
- harm；
- rescue。

自动脚本断言：

> 实际输出 == 解析值。

还必须测试：

- 3_11 / 5_10 的 CM pooling；
- 先 pool integer CM 再算 IoU；
- 禁止先算 window/tile mIoU 再平均。

Smoke test 未 PASS：

> 所有 Phase 1 正式实验禁止启动。

---

# 9. Primary metric：Same-support Missing-induced Damage

对于固定 mask \(M\)：

\[
D(M)=
mIoU^{clean}_{fg5}(M)
-
mIoU^{missing}_{fg5}(M)
\]

要求：

clean 和 missing：

> 完全在相同 mask support M 内评价。

---

## Confusion Matrix 规则

分别得到：

\[
C^{clean}_{M}
\]

和：

\[
C^{missing}_{M}
\]

先将：

`3_11 + 5_10`

的 int64 6×6 confusion matrix 相加。

然后再算：

> pooled NB mIoU_fg5。

禁止：

- 平均 sliding-window mIoU；
- 平均 tile mIoU 作为 primary；
- 用像素当独立样本。

---

# 10. Primary Endpoint

对于 paired seed \(s\)：

\[
\Delta_s^*
=
D(S_{grad,s})
-
D(U_{block,s})
\]

报告：

- 20 paired seeds mean；
- median；
- pooled effect；
- 3_11；
- 5_10；
- fg5 per-class；
- no-Car sensitivity。

---

# 11. PASS / BORDERLINE / FAIL

## PASS

同时满足：

### 1. 主效应

\[
\overline{\Delta^*}\ge+0.30pp
\]

### 2. Tile direction

`3_11 mean Δ* > 0`

且：

`5_10 mean Δ* > 0`

### 3. 不是单类别驱动

满足以下之一：

去掉 Car 后：

\[
\Delta^*_{noCar}\ge+0.15pp
\]

或者：

> fg5 至少 4 类同方向。

### 4. Supporting inference 没有明显反向证据。

---

## BORDERLINE

若：

\[
0.15\le\overline{\Delta^*}<0.30
\]

则：

- 不 PASS；
- 不 FAIL；
- paired seeds 从20扩到40；
- 所有规则、模型、q、geometry、operator、ratio 完全冻结。

---

## FAIL

若：

\[
\overline{\Delta^*}<0.15
\]

或：

- matched 后效应消失；
- 两 tile 严重反向；
- 完全由单类别推动；

则：

> Structured Failure 降级为 discussion / diagnostic。

立即停止扩展：

- 更多 structured mask；
- 更多阈值；
- 更多 failure 类型；
- 更多训练。

主线退回：

> Context-Preserving Local Adaptation。

---

# 12. Supporting Statistics

统计是支持证据，不覆盖 effect-size gate。

## 12.1 Paired Seed Permutation

统计单位：

> mask pair seed。

不是：

- pixel；
- 512 crop；
- primitive block。

对：

\[
\Delta_s^*
\]

做 paired sign-flip / permutation。

报告：

- p-value；
- mean；
- median；
- paired distribution。

解释必须写：

> 反映当前开发 tile 和 mask-generation protocol 下对 mask realization 的稳定性，不代表跨地域总体统计显著性。

---

## 12.2 Spatial Block Bootstrap

目的：

评估 tile 内空间变化。

使用：

> 大尺度 macro-block

作为 resampling unit。

不能对：

512 crop + stride256

进行普通 bootstrap。

必须明确：

- block size；
- block coordinate；
- resampling unit；
- CI 含义。

---

# 13. Healthy / Harm / Rescue

沿用 D27/D30/E0 的定义哲学。

## Healthy region

定义：

\[
Healthy =
\neg Dilate(M,8px)
\]

即 failure mask 周围 8px buffer 不计 healthy。

---

## Healthy Flip Rate

在：

> anchor 原本正确 + healthy region

中统计：

> corrupted/proposed prediction 被改错的比例。

---

## Harm Rate

继续统计：

> anchor-correct pixels 被融合或修正破坏的比例。

---

## Rescue / Retention

统计：

> anchor 错，但参考 expert / alternative modality 正确的位置，有多少被救回。

以后不能只报告 mIoU。

---

# 14. Block-size Mechanism Sweep

主实验完成后执行。

固定：

- RGB missing；
- ratio = 25%；
- zero-fill。

测试：

- 64
- 128
- 256
- 512

分别计算：

\[
D(U_{block,size})
\]

与：

\[
D(S_{grad,size})
\]

看 missing damage 是否随连续区域增大。

---

# 15. Context Bridge Experiment

这是 Phase 1A 核心实验，不是附加实验。

对 S1-0 / S1-3：

\[
CB(M)=Perf_{S1-3}(M)-Perf_{S1-0}(M)
\]

至少报告：

- U-pixel
- U-block
- S-grad
- S-boundary
- 64/128/256/512 block size

重点判断：

\[
CB(U_{block})>CB(U_{pixel})
\]

以及：

\[
CB(S_{grad})>CB(U_{block})
\]

以及 context benefit 是否随 block size 增长。

---

# 16. Mechanism Chain

如果同时发现：

\[
D(U_{block})>D(U_{pixel})
\]

\[
D(S_{grad})>D(U_{block})
\]

以及：

\[
CB(S_{grad})>CB(U_{block})
\]

则可以形成机制链：

> 连续局部失效更危险  
> → 结构性困难位置进一步放大伤害  
> → 这些区域更依赖跨区域上下文  
> → hard masking/fallback 丢失可用上下文  
> → context-preserving local adaptation 有研究必要性。

---

# 17. Phase 2 Correction Oracle

现在只算上界，不训练新方法。

## GT Composition Oracle

mask \(M\) 内：

> 使用 GT prediction。

mask 外：

> 使用 anchor prediction。

这是 local correction 的绝对上界。

---

## R0 Composition Oracle

这里的 R0 指：

> Post-S1 强 spatial-composition control。

不是 REBUILD R01。

mask \(M\) 内：

> 用 R0 prediction。

mask 外：

> 用 anchor prediction。

计算：

\[
Headroom_{R0}
=
Perf(R0Comp)-Perf(Anchor)
\]

---

## Phase 2 Headroom

若：

\[
Headroom_{R0}<0.30pp
\]

side-branch 路线降低优先级。

若：

\[
Headroom_{R0}\ge0.50pp
\]

且两 tile 同方向：

> Phase 2 有明确值得学习的 correction headroom。

---

# 18. Phase 3 Routing Oracle Ladder

当前只做 0-training 上界。

至少包括：

- Best single expert
- Probability average
- Best fixed convex ensemble
- Image-level oracle
- Patch-512 oracle
- Patch-256 oracle
- Patch-128 oracle
- Pixel oracle

重点比较：

\[
Oracle_{patch}-BestSingle
\]

和：

\[
Oracle_{patch}-BestFixedEnsemble
\]

---

## Routing Gate

只有同时：

\[
Oracle_{patch}-BestSingle\ge0.50pp
\]

和：

\[
Oracle_{patch}-BestFixedEnsemble\ge0.30pp
\]

并且：

- 3_11 > 0；
- 5_10 > 0；

才允许后续做：

> spatial router / MoE。

否则：

> routing 路线关闭。

Pixel oracle 不能单独触发 Router。

---

# 19. Descriptive Transfer Matrix

使用历史已有模型做：

| train history | Clean | U-pixel | U-block | S-grad | S-boundary |
|---|---:|---:|---:|---:|---:|

可包含：

- clean trained；
- random missing trained；
- QD/corruption trained；
- context related。

注意：

历史模型 budget / init / augmentation 不一致。

所以只能写：

> descriptive transfer matrix。

不能写：

> random missing training 导致 structured robustness 差。

---

## 若观察到明显 transfer gap

例如：

> random-trained 在 U-pixel 明显强，但在 S-grad 没有相同收益，

才允许以后补一对 matched training：

- same init；
- same optimizer；
- same updates；
- same ratio；
- 唯一变化：
  - random training
  - structured training。

没有明显信号则不新增训练。

---

# 20. Mask Availability 三档

## A. Observable-aware

推理阶段真实可以知道或从输入推导：

- known missing flag；
- sensor invalid flag；
- DSM gradient proxy；
- illumination proxy。

可以作为正式方法设定。

---

## B. Diagnostic-aware

例如：

> GT semantic boundary。

只能用于机制诊断。

禁止当成正式部署输入。

---

## C. Mask-agnostic

模型完全不知道 failure support。

这是独立问题。

Phase 1A 保留接口，但当前不要求解决。

---

# 21. Vaihingen External Replication

只有 Potsdam protocol 完全冻结后执行。

冻结：

- generator code；
- protocol version；
- q percentile；
- missing ratio；
- primitives；
- operator；
- endpoint；
- statistics；
- stop rule。

Vaihingen 不允许重新调：

- q；
- ratio；
- block size；
-模型；
- endpoint。

High gradient 使用：

> domain 内同一个 top-q%。

不是 Potsdam 绝对 threshold。

External replication 主要要求：

> effect direction > 0。

不要求必须再次达到 Potsdam +0.30pp。

---

# 22. 第一轮执行顺序

### Step 1

只读检查当前服务器和 GitHub：

- branch；
- HEAD；
- current queue；
- F/H/R 是否仍运行；
- GPU 使用；
- checkpoints；
-已有 predictions。

不进行任何写操作到当前运行目录。

### Step 2

创建冻结协议：

`docs/protocols/STRUCTURED_FAILURE_EVAL_V0_20261011.md`

提交后 protocol version 固定。

### Step 3

实现 canonical mask generator。

建议新目录：

`records/structured_failure_protocol_v0/`

生成：

- `protocol.json`
- `mask_registry.json`
- masks
- generator validation

### Step 4

运行 known-answer smoke test。

只有 PASS 才继续。

### Step 5

生成 Potsdam：

- 20× U-pixel
- 20× U-block twins
- 20× S-grad
- 20× S-boundary

### Step 6

先跑四个模型：

- RGB-only
- Dual anchor
- S1-0
- S1-3

### Step 7

计算：

- CE
- Δ*
- CB
- per-class
- no-Car
- healthy flip
- harm
- rescue

### Step 8

做：

- paired-seed permutation
- spatial block bootstrap

### Step 9

按预注册 PASS/BORDERLINE/FAIL 裁决。

### Step 10

计算：

- GT correction oracle
- R0 correction oracle
- routing oracle ladder
- best fixed convex ensemble

### Step 11

若 pipeline 合法且 continuity/context 至少有明显信号，再做：

- 64/128/256/512 block-size sweep。

### Step 12

F/H/R 完成后，按原 F/H/R protocol 独立验收。

Phase 1A 结果不得影响 F/H/R 判定。

之后才决定是否加入 H/R representative。

---

# 23. 第一轮必须输出的表

## Table A — Mask Protocol

| family | geometry | placement | ratio | availability | seeds |
|---|---|---|---:|---|---:|

## Table B — Continuity Effect

| model | D(U-pixel) | D(U-block) | CE |
|---|---:|---:|---:|

## Table C — Primary Content-location Effect

| model | D(U-block) | D(S-grad) | Δ* | 3_11 | 5_10 | verdict |
|---|---:|---:|---:|---:|---:|---|

## Table D — Per-class Δ*

| model | Imp | Bld | LowVeg | Tree | Car | no-Car |
|---|---:|---:|---:|---:|---:|---:|

## Table E — Context Bridge

| mask | S1-0 | S1-3 | Context Benefit |
|---|---:|---:|---:|

## Table F — Capability Preservation

| model | mask | mIoU | healthy flip | harm | rescue |
|---|---|---:|---:|---:|---:|

## Table G — Correction Oracle

| mask | anchor | R0-comp | GT-comp | R0 headroom | GT headroom |
|---|---:|---:|---:|---:|---:|

## Table H — Routing Oracle

| granularity | score | vs best single | vs fixed ensemble |
|---|---:|---:|---:|

---

# 24. 必须输出的图

至少输出：

1. Block size vs missing-induced damage
   - U-block
   - S-grad

2. Block size vs context benefit
   - S1-3 − S1-0

3. Paired-seed Δ* distribution

4. Per-class Δ*

图仅用于解释。

不能替代主 endpoint。

---

# 25. Phase 1 结果后的三个分支

## Branch A — Structured Failure PASS

如果 Δ* 按冻结规则 PASS：

下一阶段主问题升级为：

> **Structured Partial Modality Failure + Context-Preserving Capability Adaptation**

Phase 2 优先：

- frozen strong anchor；
- local residual side branch；
- healthy-region anchor distillation；
- damaged-region correction；
- condition-matched R0 teacher；
- side branch 深度由 F/H/R 决定。

---

## Branch B — Structured Failure FAIL，但 Context Benefit 成立

如果：

- Δ* FAIL；
- 但 CE / CB 明显存在；

则：

structured missing 降级到 discussion。

论文主线回到：

> **Context-Preserving Local Modality Adaptation**

停止继续扩 structured masks。

---

## Branch C — Structured 与 Context 都弱

如果：

- CE≈0；
- Δ*≈0；
- CB≈0；

停止这一方向继续扩展。

回到 F/H/R：

> representation adaptation / capability preservation

重新判断 RGB–DSM 鲁棒融合主线是否值得继续。

---

# 26. Phase 2 预留方案——现在禁止执行

只有 Phase 1 与 F/H/R 都完成后再决定。

候选：

> ConD-inspired local residual side branch。

要求：

- frozen anchor；
- zero-init residual；
- side branch 只做 local correction；
- damaged region 可读取 surrounding context；
- healthy region 做 anchor distillation；
- damaged region 用 task supervision；
- condition-matched R0 distillation 作为 cheap baseline；
- matched-capacity control；
- no-context control；
- random-mask control。

初步 gate：

- structured/local missing ≥ no-branch +0.5pp；
- clean loss ≤0.1pp；
- healthy flip 不恶化；
- 两 tile 同方向。

这里只预留。

现在不得训练。

---

# 27. 执行完成后必须回传给用户

必须报告：

1. branch / HEAD。
2. 是否触碰 F/H/R 队列：必须 NO。
3. 新 protocol 文件路径。
4. protocol commit。
5. mask generator 路径。
6. generator commit。
7. registry。
8. smoke test PASS/FAIL。
9. mask family 实际像素数与 geometry。
10. 20 paired twins 完整性。
11. 四模型 evaluation 完成情况。
12. Table A–H。
13. CE。
14. Δ*。
15. 3_11 / 5_10。
16. per-class。
17. no-Car sensitivity。
18. paired permutation。
19. spatial bootstrap。
20. CB。
21. correction oracle。
22. routing oracle。
23. 根据冻结规则明确给出：
   - Structured PASS / BORDERLINE / FAIL；
   - Phase 2 是否值得；
   - Router 是否允许继续。
24. 明确列出本轮**没有执行**的实验。

禁止使用：

> “看起来有效”“可能可以”“建议继续试”

代替冻结 gate。

---

# 28. 本阶段最重要的原则

这轮实验不是为了寻找一个涨点网络。

而是准确测量：

\[
CE=D(U_{block})-D(U_{pixel})
\]

\[
\Delta^*=D(S_{grad})-D(U_{block}^{matched})
\]

\[
CB(M)=Perf_{S1-3}(M)-Perf_{S1-0}(M)
\]

只有先证明：

> 连续局部失效是否更危险；

再证明：

> 内容相关位置在 footprint matched 后是否仍更危险；

再证明：

> context preservation 是否恰好缓解这一类困难；

才允许进入下一阶段网络设计。

如果 structured hypothesis 不成立，必须按 stop rule 停止，不得继续增加 failure 类型、阈值、seed 或模型去寻找正结果。