> 历史快照，来自1a8a840；其中下一步安排已由当前研究定位澄清替代，不作为当前执行指令。

# Start Here

## 先读实验准备规则

[实验规划与服务器准备规则](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/protocols/EXPERIMENT_PLANNING_RULES.md)：正式排队前先测吞吐；
探索默认单种子，多种子说明必要性；下载/环境提前说明并单独准备。
服务器优先访问 GitHub/Hugging Face，不可达来源可经 Colab → Hugging Face 中转。
[新实验准备表](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/templates/EXPERIMENT_PREFLIGHT_TEMPLATE.md)用于落实这些要求。

D21 有效双种子范围已完成32/32并归档；F2未通过预设开发门槛。
原48项队列的 `32/48 INCOMPLETE` 是停止第三种子后的历史状态。
Post-D21 多方向42项与混合退化后续4项已在服务器报告完成，整数审计均为 PASS；随后逐 tile CPU 审计也为 PASS；见[最终开发集分析](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/experiments/POST_D21_FINAL_AND_MIXED_FOLLOWUP_RESULTS_20261001.md)及[局部风险](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/experiments/POST_D21_MIXED_TILE_RISK_RESULTS_20261001.md)。目前准备独立来源验收，不自动追加训练。

- [当前交接](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/current/HANDOFF.md)
- [Post-D21 最终开发集分析](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/experiments/POST_D21_FINAL_AND_MIXED_FOLLOWUP_RESULTS_20261001.md)
- [混合退化逐 tile 风险](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/experiments/POST_D21_MIXED_TILE_RISK_RESULTS_20261001.md)
- [D21结果报告](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/experiments/D21_DETAIL_FREQUENCY_RESULTS_20260929.md)
- [下一步有界吞吐测试](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/protocols/POST_D21_THROUGHPUT_PROBE_20260929.md)
- [吞吐短测结果](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/experiments/POST_D21_THROUGHPUT_PROBE_RESULTS_20260929.md)
- [已执行的多方向一天以上实验计划](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/protocols/POST_D21_MULTIDIRECTION_DAY_PLAN_20260929.md)
- [多方向实验服务器准备、短测与启动](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/protocols/POST_D21_DAY_EXECUTION_20260929.md)
- [旧 D22 草案（已由多方向方案替代）](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/protocols/D22_STRUCTURE_ALIGNED_DSM_RELIABILITY_DRAFT_20260929.md)
- [执行协议和一键启动](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/protocols/D21_DETAIL_FREQUENCY_DAY_QUEUE_20260928.md)
- [当前状态](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/current/PROJECT_STATUS.md)
- [下一步与结果判断](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/current/NEXT_EXPERIMENT.md)
- [不可重复事项](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/current/DO_NOT_REPEAT.md)
- [实验索引](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/experiments/rebuild_v1/INDEX.md)

GAMUS 来源验收只影响其作为外部确认数据的资格，不阻塞已有数据的开发实验。
Test6 继续封存。此前长篇状态和命令归档于 [历史入口](https://github.com/66322/remote_sensing_frequency/blob/1a8a840/docs/history/20260928_before_d21/START_HERE.md)，不代表当前操作。
