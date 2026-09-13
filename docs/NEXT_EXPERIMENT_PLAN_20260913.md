# 下一阶段实验计划（2026-09-13）

主记录：`docs/EXPERIMENT_MASTER.md`。

## 当前结论

主线为 **Optical/DSM Cross-modal HF Reliability + Rare30**。

- Vaihingen 10k：NB mIoU_fg5 = **83.0658**。
- Potsdam 10k：baseline 85.9045；HF Reliability 85.2439；HF Reliability + Rare30 **86.0306**。

关键矛盾：HF Reliability 在 Potsdam 单独使用相对 baseline **-0.6606**，加 Rare30 后才回升并略超 baseline（+0.1261）。因此下一步应优先解释跨数据集/跨类别 reliability 不稳定，而不是继续堆浅层细节模块。

## 下一阶段优先级

### E50｜Corruption / modality reliability audit（最高优先级，不训练）

用现有 baseline、HF Reliability、HF Reliability+Rare30 checkpoint，测试：DSM blur、DSM downsample×2→resize、DSM shift 2/4 px、DSM zero、Optical blur、Optical downsample×2→resize。

记录 Full/NB OA、mF1_fg5、mIoU_fg5、per-class IoU、confusion matrix，以及 mean/per-class `wo/wd`、reliability gap、discrepancy、discrepancy-gap correlation。

原因：先证明当前 gate 是否真的感知“模态质量”。若 DSM 变差时 `wd` 下降、`wo` 上升且性能下降更慢，才支持 reliability 机制解释。

### E51｜Potsdam HF Reliability：3×3 → 5×5（10k）

当前高频为 `high = x - AvgPool3×3(x)`。Vaihingen GSD≈9 cm，3×3≈27 cm；Potsdam GSD≈5 cm，3×3≈15 cm。两数据集中的“高频”并非同一物理尺度。

最小验证：Potsdam 只改 HF kernel 3→5，5×5@5 cm≈25 cm，接近 Vaihingen 3×3@9 cm≈27 cm。先不加 Rare30，其余设置完全不变。

原因：若 k5 能恢复当前 k3 在 Potsdam 上的退化，则支持“固定像素频率尺度不能稳定跨 GSD 工作”的核心假设。

### E52｜Potsdam physical-scale HF + Rare30

仅在 E51 出现正向趋势后做。与当前 Potsdam 最优 86.0306 比较，判断 physical-scale correction 与 Rare30 是否互补。

### E53｜同一数据集 synthetic-GSD controlled audit

优先 Potsdam。保持同一 test set/label，只改变输入有效空间分辨率（downsample→upsample 若干档位）。比较 baseline、pixel-scale HF、physical-scale HF，画 `mIoU vs effective GSD`。

原因：Vaihingen vs Potsdam 还混有 IRRG/RGB、城市、纹理、类别分布等差异，不能单独证明 GSD 因果。

### E54｜Modality-resolution mismatch

固定 Optical，只降低 DSM 有效分辨率；再反向固定 DSM、降低 Optical。同步观察 mIoU 与 `wo/wd`。

原因：直接验证模态质量变化时 gate 是否把权重移向更可靠模态。

### E55｜真正的 GSD-aware / physical-scale HF Reliability

仅在 E51–E54 支持假设后设计。可考虑 `k=f(GSD)`、按 `GSD×feature stride` 统一真实空间尺度，或用 15/30/60 cm 等物理尺度而不是固定 3/5/7 kernel。

主线升级为：**Frequency Reliability → Physical/GSD-aware Frequency Reliability → Robustness under modality quality mismatch**。

## 暂缓方向

暂不继续：Normal/HF Shallow Detail、History sampling、Rare30 比例搜索、继续堆 decoder frequency、立即切 DINOv3/SAM2/Mamba、直接把 class-conditioned reliability 当主创新。

Foundation Model 更适合主线稳定后，以 frozen encoder + Adapter/LoRA 验证 backbone generality。

## 新对话接手顺序

新对话先读取：
1. `README.md`
2. `docs/EXPERIMENT_MASTER.md`
3. 本文件
4. 最新 `records/`
5. 准备运行实验对应的 `model/` 与 `scripts/`

不要根据 P1/P2H/ScreenV2 等历史名字猜实验含义，以主记录正式描述为准。

## 是否需要重新审计路径

**不需要从零重做全项目审计，但正式运行下一轮实验前必须做轻量 preflight audit。**

必查：
- `git status` / 当前 commit，确保服务器代码与 GitHub main 一致；
- 项目根目录；
- Vaihingen/Potsdam Optical、DSM、GT、NoBoundary GT 路径；
- train/test tiles 是否齐全；
- `R50+ViT-B_16.npz` 是否存在可读；
- 当前 baseline / HF / HF+Rare30 checkpoint 是否存在；
- trainer 引用 model 是否正确；
- crop=512、seed=42、batch/grad accumulation/optimizer step 口径；
- `CUDA_VISIBLE_DEVICES=0`；
- smoke test 通过后再跑正式 10k。

E50 额外要求：corruption 只能作用于 evaluation input，不能改 label；normal 条件必须先复现已有结果。

E51 额外要求：除 HF kernel/physical-scale 定义外，公共参数逐项对齐原 Potsdam HF Reliability；neutral/identity initialization 保持不变；先做 deterministic smoke pair。

## 立即执行顺序

**E50 → E51 → E52 → E53 → E54 → E55 → 新方案稳定后做 ≥3 seeds → 最后再考虑 Foundation Model 迁移。**
