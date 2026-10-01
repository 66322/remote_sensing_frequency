# D23当前状态与交接（2026-10-01）

分支rebuild-v1-protocol-20260915；实验基准1a8a840，A工具961c719，GPU吞吐探针526d5a0。用户终端执行，本地无服务器直连。

研究仍是可行性探索：优先频率＋语义可靠性、模态退化/缺失训练与推理；C1旁支，部分解冻强基线，允许换解法/交叉问题/方向。章节和贡献未冻结。见[决策](RESEARCH_DECISION.md)。

D23-A最后带时钟观测2026-10-01T12:44:35.075903+08:00 COMPLETE：Potsdam Val2、R0/M0 seed42 final16000、NoBoundary fg5，标签选择诊断clean +1.592737/rgb_down4 +2.415542/noise +1.657089pp，平均+1.888456pp，通过准备B投入条件。不是learned gate、语义或频率成立证据。原件仍服务器；A轻量归档报告SHA041bc0ad79c3c5f11fdbf4a29479b2c3cf68d60f898b5125d8cf2211e59084b1，尚未收到本地。不重跑A。

最新用户回传GPU日志未给结束时钟：GPU0 micro2/4/8短测完成，micro16因expert decisions changed across steps/microbatches停止；GPU1未启动。无OOM证据，不能确认数值误差原因。用户确认两卡H100、内存/磁盘充足；仍须执行时核对空闲。原目录records/research_d23_b_crop_probe_20261001T131740_658274保留。见[GPU结果与诊断](../experiments/D23_B_GPU_DIAGNOSTIC_20261001.md)。

B核心CPU8测试在本地/服务器通过；probe准入及像素诊断本地5测试通过。已实现--decision-audit-only，下一步两卡分别对micro2/4/8/16逐像素比较并重复两次，不训练gate，不保存权重。跨微批差异原样记录，同一微批预测不稳定仍停止。旧crop吞吐矩阵不重跑，micro8仅候选，未冻结。

完整训练/14条件整图评价入口、TCAP fit统计、固定采样流、滑窗拼接后精确回退、整图与双卡资源预算未完成，正式8组4000步队列未启动。原收益/风险/机制门槛保持；频率无独立增量撤回其贡献，gate无收益关闭解法，不自动补seed或调阈值。见[下一实验](NEXT_EXPERIMENT.md)。

旧Test6已历史暴露，禁读且无独立final资格；Post-D21原摘要等归档缺口仍存在。第一轮光学可用、已知DSM mask回退；未知缺失、光学全缺失与独立来源泛化仍未验证。

全部服务器快照/日志/JSON/归档保存在/home/jovyan/zzx下的对应实验目录；新诊断目录records/research_d23_b_decision_audit_<timestamp>_<pid>。不覆盖或移动原产物。上一交接见固定526d5a0版本。
