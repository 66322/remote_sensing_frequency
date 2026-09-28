# 当前交接：D21 细尺度高度与频率对照

记录于2026-09-28。用户授权物理 GPU0/1，可连续运行超过一天。
**状态：代码和队列已准备，CPU合同测试通过；服务器环境/真实CUDA完整链尚待启动器验证，没有训练已启动证据。**

## 立即执行

在服务器工程目录、remote_sensing 环境拉取当前分支后运行：

```bash
mkdir -p records/rebuild_v1_d21_queue_20260928
nohup bash scripts/run_rebuild_v1_d21_queue.sh > records/rebuild_v1_d21_queue_20260928/launcher.log 2>&1 < /dev/null &
echo $!
tail -n 50 records/rebuild_v1_d21_queue_20260928/launcher.log
```

完整命令、资源、停止和恢复方法见[协议](../protocols/D21_DETAIL_FREQUENCY_DAY_QUEUE_20260928.md)。
脚本自动复用 d18_dino 环境和权重，核对两套现有数据，完成16个短流程后跑32组；不需要逐轮回来批准。
每组16k，两个种子42/17，两个数据集Potsdam/Vaihingen；粗估20–35小时，最终以实测吞吐为准。

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

旧交接全文保留于[历史归档](../history/20260928_before_d21/HANDOFF.md)。
