# 下一实验：Phase 1.5 Recoverability Decomposition

状态：**PHASE_1_5_FROZEN_AWAITING_SMOKE_IMPLEMENTATION**。

Post-T paired v2 与 Structured Failure v0.1 均已完成科学收口；当前没有运行中、已登记或自动等待的新实验。Phase 1A 的 structured-location vulnerability 按预注册规则关闭，不扩样、不改阈值、不换 mask 追正。

新的唯一下一研究问题不是“直接训练 reliability/quality-aware fusion”，而是：

> **在局部 RGB missing 下，S1 剩余约 21 pp 的伤害有多少是当前输入/专家体系下可恢复的；25% missing 是否存在饱和；伤害主要位于 mask 边界还是内部；现有 frozen experts 之间是否存在足够且可学习的互补空间，值得重新打开 routing/reliability 主线？**

完整冻结协议：

- [Phase 1.5 — Recoverability Decomposition under Local RGB Failure](../protocols/PHASE_1_5_RECOVERABILITY_20261012.md)

## 固定子实验

1. **1.5-E Spatial damage profile**：S1-0，按到 mask 边界距离分箱，区分 edge-dominant 与 approximately-uniform damage；优先复用 Phase1A 预测，能离线复算则不占 GPU。
2. **1.5-A DSM intervention**：S1-0 primary，R16 secondary；DSM intact / crop-shuffle / tile-shuffle / zero，复用 Phase1A 20 realization，回答 DSM 内容/空间对应是否参与抑制结构敏感性。
3. **1.5-B Ratio response**：S1-0，pixel mask only，严格 nested `M5 ⊂ M10 ⊂ M25`，20 realization；分析 dose-response 与 saturation，不把 block size 混进 ratio。
4. **1.5-C Per-class decomposition**：五类全报，primary contrast = Car−Building；持久化 per-realization per-class confusion matrix。现有 D15 DSM-only 默认按 legacy checkpoint 处理，不能冒充 information-theoretic upper bound。
5. **1.5-D Oracle headroom + learnability**：oracle pool `{S1-0, S1-3, DSM-only, RGB-only, R16}`；raw known-mask selector、GT per-pixel/per-patch oracle、条件胜率分析。GT class/真实 mask geometry 仅用于机制诊断，不能单独作为部署可学习性证据。

## Routing/reliability gate

raw 5-expert per-pixel oracle：

- `<2 pp`：默认关闭；若结论受 legacy DSM-only 限制则只记 provisional close。
- `2–6 pp`：gray zone，不自动训练 router。
- `≥6 pp`：只获得 conditional entry；还必须看到 deployment-observable 条件下跨两 tile 可重复的 expert preference，才允许进入下一次独立设计评审。

`≥6 pp` 不是方法成功，更不是自动训练许可。

## Smoke gate

正式全量前只允许 **1 个 realization** 做工程 smoke/known-answer；它不能用于估计 realization 方差或科学效应。

smoke 必须通过协议中固定的 archived replay、M25 SHA identity、nested mask、shuffle bijection、distance-transform toy、oracle toy、composition identity、seam smoothing containment、confusion conservation、zero-training、data isolation、checkpoint binding 等检查。

任一 FAIL：`SMOKE_FAILED_HOLD`，不得边跑全量边修。只有 smoke 全 PASS 后，才允许登记全量 Phase 1.5 zero-training 推理。

## 当前不要做

- 不训练 reliability estimator / αβγ soft gate。
- 不新增 side branch / adapter。
- 不盲目重训 DSM-only；matched DSM-only 只允许成为 Phase1.5 结束后的条件性后继。
- 不追加 seed/realization，不改 Phase1A gate。
- 不用 smoothed composition 覆盖 raw oracle gate。
- 不访问 Test6 / held4 / final。

Phase 1.5 全部结果回收后，再在 `capability-preserving residual context adaptation` 与 `conditional routing/reliability` 之间做正式主线选择。