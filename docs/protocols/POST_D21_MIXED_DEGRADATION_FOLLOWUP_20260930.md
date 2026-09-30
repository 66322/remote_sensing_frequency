# C1 恢复收益的混合退化泛化实验

状态：根据 Post-D21 队列 A/B/C 的 **36/42 阶段开发结果**提出并在下一组训练前冻结问题；尚未在服务器准备、短测或运行。D 的剩余配对仍在原队列执行，不用其中途结果选择本方案。

## 研究问题和范围

C1（可学习前端+分割 CE）相对 C0（固定双三次+分割 CE）在两个数据集的固定 ×2、×4 任务上均为正，范围 +0.228 至 +0.768 个 mIoU 百分点。C3 高频监督四块均未通过预设门槛，因此本轮只检验 **C1 的收益能否迁移到训练时混合倍率与模糊、推理时未见模糊**。这不是重复 C 的固定倍率任务，也不是将 C3 的负结果改写为成功。

从原计划中未纳入正式 42 项的 E 储备清单，单独取 `E_{potsdam,vaihingen}_{bicubic_ce,learned_ce}_scale0_seed42` 四项，按数据集和模型成对训练。**四项子集的选择已参考本轮 C 的开发结果，故属于新的探索性实验，不沿用原八项 E 块的预结果范围冻结声明。**每项 16k 更新、有效 batch16、同一 seed42；模型与退化设置、输入、优化器、评价代码沿用已审计的 E 实现。训练时按固定 0.5/0.5 概率选择 ×2/×4，以及 0.5 概率的 sigma=1.0 模糊；评价固定为 ×2/×4 各自 clean 和训练未见的 sigma=2.0 模糊。所有组使用相同设置，最终步 checkpoint，不从开发得分提前停止。

主指标分别为 Potsdam Val2 NoBoundary fg5 mIoU 与 Vaihingen 同镶嵌图开发区 FullGT fg5 mIoU。逐条件报告 C1−C0 的百分点差、每 tile 混淆矩阵与负迁移、checkpoint SHA、训练/评价绑定、恢复诊断。四种条件各自报告，不把不同倍率或模糊条件混成单一分数；若做四条件均值，只作为描述性汇总。单种子开发证据不得宣称独立泛化、统计显著或论文确认性 test。

## 执行边界

- 原 42 项队列必须先以 `QUEUE COMPLETE 42/42` 退出，避免两卡争用和截断 D 的交互对照。新组**另有独立队列记录与完成标记**，不得改动原 `scope.json`、原 run、原 checkpoint 或 D21 证据。服务器 pull 新提交前需确认它只新增后续执行器与文档，不改原计划中已冻结源码。
- 只用现有 Potsdam/Vaihingen、DINO 和旧队列输入资产；不自动下载或安装。物理 GPU0、GPU1 各一个进程；先在训练 tile 做四路径 smoke，再执行四项正式训练及开发评价。原队列吞吐仅用于粗略预计，本组真实时间由进度记录显示，不能为填时长增加 seed 或空转。
- 每任务前检查原代码/输入/设备 UUID 绑定、磁盘、可用主机内存和 GPU 空闲；技术失败停止新队列。STOP 仅阻止后续任务，不强杀当前训练。保留完整预测和权重在服务器，仅同步紧凑记录到 GitHub。Test6 和独立 final 不加载。
- 原队列若以 `INCOMPLETE` 退出，后续队列不自动启动，应先处理故障。A 的 DSM 与灰度差值和 D 的最终交互另行分析，不从本组推断高度机制。

## 服务器准备和启动

本次提交只新增执行器和文档，不更改原队列已冻结的源码与配置。原目录可拉取后先运行 CPU/资源准备；准备不启动 GPU，也不修改原队列。**逐条**执行以下命令，确认每条完成后再输入下一条：

```bash
git pull --ff-only origin rebuild-v1-protocol-20260915
python -B scripts/run_rebuild_v1_mixed_followup.py --prepare-only
nohup python -B -u scripts/run_rebuild_v1_mixed_followup.py --launch > records/post_d21_mixed_followup_queue_20260930/launcher.log 2>&1 < /dev/null &
```

启动器会等待原队列释放独占锁，然后检查其 `QUEUE COMPLETE 42/42` 及零失败。若原队列失败或未形成完成摘要，新组直接退出，不会占用 GPU。先做四项训练 tile smoke，再成对正式训练。队列 `status.tsv`、`progress.json`、`queue_summary.json` 在 `records/post_d21_mixed_followup_queue_20260930/`；整数审计和四条件成对差值在 `records/post_d21_mixed_followup_compact_20260930/analysis.json`。若准备阶段拒绝，检查报错，不修改原计划或重建已有产物。

下轮的设计与阶段证据见[早期分析](../experiments/POST_D21_EARLY_AB_C_RESULTS_20260930.md)。
