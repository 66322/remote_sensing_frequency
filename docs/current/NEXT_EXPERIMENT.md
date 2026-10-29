# 下一步：先检验新增能力，按小批次决定投入（2026-10-29）

[完整研究计划](../experiments/POST_M2_CAPABILITY_PRIOR_PLAN_20261029.md)、[证据/近邻核对](../experiments/POST_M2_EVIDENCE_AND_LITERATURE_AUDIT_20261029.md)、[准备表](../protocols/POST_M2_CAPABILITY_PREFLIGHT_20261029.md)为最新规划。状态PROPOSED_NOT_IMPLEMENTED_NOT_LAUNCHED，本轮没有新训练或队列。

建议先实施A0：冻结DINOv2与一个规模尽量接近的DINOv3，用同头/同视野探针检查分割读出与空间关系，训练内校准不参与梯度。再做A1四臂：强RGB、普通RGB–DSM、RGB+外部上下文、RGB–DSM+外部上下文。必须匹配普通上下文、有效容量、样本流和充分训练预算；不能仅在弱RGB上加大模型后归因知识。

默认seed42/F0。A0两浅层探针4k；A1四臂32k；阳性才做普通教师与空间错配两控制16k。名义合计8作业/52k，额外教师/专家重建另计，尚未有执行代码。先第二地理开发折，再按必要性成对补seed17；不默认第三seed。F0/F1不是独立最终检验，封存split不开放。

具体可执行准备：冻结教师来源/预训练暴露、训练内划分与空间缓冲、输入与DSM单位、评价mask/指标、配对接口、真实吞吐和分批停止。仅有计划不能运行旧合并队列代替。后续B几何/C蒸馏/D频率/E优化/F地图维护均按证据条件进入，不自动全排。

## 仍待回执的已授权收尾

[离线补充分析与最终清理](../experiments/PHASE3_M2_FINAL_COMPACTION_20261029.md)已有实现和12项本地检查，但未收到服务器执行结果。原scripts/compact_phase3_m2.py --apply任务先保存小统计后删除剩余运行权重和大统计，不训练/推理、不修J、不反复哈希。目标0权重，最后实际18；没有回执不能提前宣称完成。

收到GITHUB_RELAY_SUMMARY或analysis_summary.json/cleanup_result.json后，把实际补充结论、回收量与retention更新到GitHub。新规划不要求保留无用旧权重；未来要用的参考模型须合法复用或明确计入最少重建成本。没有服务器直连，本地发布文件不等于服务器清理或训练成功。
