# START HERE：双模态主问题已纠正，D26复用现有专家的建议

更新2026-10-02；权威分支rebuild-v1-protocol-20260915。用户纠正“只围绕DSM退化”以及“又做单模态实验”的倾向。主问题为**RGB与DSM双方信息的互补学习及任一方退化/缺失下的分割**；RGB始终可用仅是D23—D25阶段条件。双向设计不要求两种模态同骨干或同精度。

读取顺序：
1. [研究定位与决定](current/RESEARCH_DECISION.md)
2. [当前交接](current/HANDOFF.md)
3. [当前状态](current/PROJECT_STATUS.md)
4. [下一步](current/NEXT_EXPERIMENT.md)
5. [D15—D25已经得到的结论](experiments/RESEARCH_SYNTHESIS_D15_D25_20261002.md)
6. [D26具体建议](protocols/D26_BIDIRECTIONAL_FEATURE_PLAN_20261002.md)、[近期原论文及交叉研究](literature/D26_BIDIRECTIONAL_COMPLEMENTARITY_20261002.md)

D15已做两seed DSM-only，D18已有RGB/灰度/DSM对照，D24 C0、D25 P6有适配RGB-only。优先复用权重和结果，不重训“单模态有没有用”。D26建议复用P6与D15 DSM专家，九组双模态特征融合/联合适配/容量/语义×频率/打乱对照；仅规划，未实现、未启动，不重复旧队列。

最后服务器观测仍2026-10-02T15:14:54.351476+08:00 D25 COMPLETE8/8，原件2290b39、复核39ed183。D25四screen失败保持；C1旁支，最终贡献未冻结。Test6禁读，Val2/历史held4不独立。

GPU0/1两H10080GB，RAM/磁盘充足；长任务nohup，所有产物在zzx对应目录，无需重新资源准入审计。
