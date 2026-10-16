# 当前交接：D21 细尺度高度与频率对照

更新于2026-09-29。用户授权物理 GPU0/1，可连续运行超过一天。
**最后观测：2026-09-29 12:41:31 +08:00，用户贴出的进度显示两卡正在运行 seed17 M1。**
Potsdam为6,800/16,000步，Vaihingen为6,200/16,000步；waiting=8、stop_requested=false。
这是最后收到的服务器记录，不是实时状态；未收到最终完成证据。

## 当前操作

服务器实际从旧提交 `10f63ea` 的48任务队列启动，16项smoke已通过，正式训练于9月28日22:55开始。
已配置额外监视脚本，等seed17的16项正式任务全部开始后写STOP，再让当前任务完成。
当前保持运行，勿在该检出拉取/修改源码，勿重新启动队列。
等旧队列最后记录 `QUEUE INCOMPLETE 32/48` 后，再执行：

```bash
git pull --ff-only origin rebuild-v1-protocol-20260915
python -B scripts/finalize_rebuild_v1_d21_two_seed.py
```

完整命令、资源、停止和恢复方法见[协议](../protocols/D21_DETAIL_FREQUENCY_DAY_QUEUE_20260928.md)。
收尾脚本保留旧计划/状态，核对32项检查点及计数后记录两种子有效范围32/32；不重新训练。
本批每组16k，两个种子42/17，两个数据集Potsdam/Vaihingen。原来的估时不视为实时剩余时间。

## 后续实验必须采用的新规则

[实验规划与服务器准备规则](../protocols/EXPERIMENT_PLANNING_RULES.md)是2026-09-29用户明确要求：
先做服务器吞吐测试再冻结批次/累积/预取；默认单种子，多种子须说明具体原因；
下载和环境安装提前说明，准备完成后再安排训练队列。优先已有缓存和GitHub/Hugging Face，
无法直连时可用Colab下载并经Hugging Face中转。使用[准备表](../templates/EXPERIMENT_PREFLIGHT_TEMPLATE.md)。

## 已知依据与边界

- D18 双seed显示 DSM 互补增益；全缺失时仍有退化。
- D20 Vaihingen旧P0/P1/P2的seed42逐tile门槛失败，保留原判，不追加原8k复验。
- D21 新机制是冻结DINO下1/4尺度高度特征及高低频对应关系，所有基线在同一16k预算重跑。
- D12旧冻结专家头、D16/D17一致性/梯度监督、D19局部交互失败，不重启这些配方。
- GAMUS元数据核查结束，不重复；其来源问题不再阻塞已有数据开发实验。
- Test6/独立final均未开放；32组输出仍是重复开发证据。第三种子不自动运行。

## 回传

观察日志 `records/rebuild_v1_d21_queue_20260928/launcher.log`，训练状态在 `progress.json`。
每个seed块后生成 `records/rebuild_v1_d21_compact_20260928/metrics.csv`、`decision.json`。
结束后只将 compact 目录提交到当前 GitHub 分支，命令见协议。运行中勿修改/拉取冻结源码。

上版交接保留于[历史归档](../history/20260929_before_policy/HANDOFF.md)。
