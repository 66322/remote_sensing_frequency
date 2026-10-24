# D20-V Vaihingen 匹配三组短流程

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: plan/run preparation
- Origin Date: 2026-09-28
- Verification Status: IMPLEMENTED_LOCAL_CHECKS_ONLY; server CUDA smoke pending
- Version Label: v1

Vaihingen 17 个候选块已于服务器通过内容采样检查，原始记录在 `66ac041`，
交接修正在 `6298bb4`。所有候选与旧实验区域同属一幅镶嵌图，
本短流程仅验证开发实验基础设施；不会给出跨城市确认结果。

## 已冻结的短流程输入

- P0：TOP 三通道；P1：TOP + 由这三通道求平均的辅助灰度；
  P2：TOP + DSM。P1/P2使用同一冻结 DINOv2 ViT-S/14 骨干和辅助结构。
- TOP 按原 TIFF 顺序近红外、红、绿输入，除以255，然后沿用原 DINO 模型的
  三通道均值/标准差。这是明确的迁移假设，不能称作真 RGB。
- DSM 按每幅图自己的最小/最大值归一化到0–1，与本仓库旧 Vaihingen 加载器一致。
  这只使用输入影像，不读取开发区标签统计来设参数。
- 训练区沿用旧 F0/P1 的12个 ID：`1,3,7,11,13,17,23,26,28,32,34,37`。
  开发候选为17个旧实验未用 ID：`2,4,6,8,10,12,14,16,20,22,24,27,29,31,33,35,38`。
  旧评估 ID `5,15,21,30` 排除。此切分是同一镶嵌图的开发切分，
  不作为独立最终验证。
- 训练标签用 `gts_for_participants`；开发标签用 `gts_complete_full`。
  不把 `noBoundary` 标签误作完整标签。所有有效像素必须匹配六类调色板。

配置保存在 `configs/rebuild_v1/d20_vaihingen_development_smoke_20260928.json`。
本轮仅 seed42、每组一步、训练 ID1 一个512块、开发 ID2 一个512块。
每组一步同时覆盖 clean 与 aux_down4 两条训练分支，然后验证训练梯度、
权重保存、重新加载和混淆矩阵计算；结果不用于选择方法。
三组共享相同的采样规则及模型初始化种子。GPU0/1独立运行 P0/P1，
P2 接续 GPU0；任何前置失败都阻止 P2。完整正式预算、全区域评价和
seed17必须在短流程通过后另行冻结并实现，不由本脚本自动启动。

## 服务器入口

在项目根目录运行：

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
conda activate remote_sensing
git pull --ff-only origin rebuild-v1-protocol-20260915
bash scripts/run_rebuild_v1_d20_vaihingen_smoke.sh
```

队列会寻找既有 `d18_dino` Python，核对数据清单和 GPU0/1，绑定代码/配置哈希。
状态与日志写入 `records/rebuild_v1_d20_vaihingen_smoke_20260928/`；
`records/rebuild_v1_d20_vaihingen_smoke_compact_20260928/`自动收集状态、
执行提交及每组摘要，供 GitHub 交接。权重放在
`runs/rebuild_v1/D20_VAI_SMOKE_<arm>_seed42_20260928/`，仅留服务器，不进入 GitHub。

退出后检查 `status.tsv` 的 `SMOKE_GATE COMPLETE` 及三组摘要；
若失败保留日志，不把失败组当作研究结果。短流程通过后，下一阶段才制定
正式训练预算、完整条件评价、各类与逐区域指标及停止门槛。
