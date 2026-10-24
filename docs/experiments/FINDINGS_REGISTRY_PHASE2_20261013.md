# Phase2衔接发现登记（2026-10-13）

此处登记可追溯的局部发现，不替代研究主线决定。所有科学运行限定Potsdam fit12/Val2两tile、seed42；下面没有新训练或独立泛化结果。

| ID | 分级 | 证据与可声称内容 | 边界 |
|---|---|---|---|
| F-DSM-ALIGNMENT-DEPENDENCE | 实验已验证：固定模型输入敏感性 | S1 RGB缺失ROI damage intact21.6516pp、crop-shuffle71.8727、tile-shuffle76.5784、zero79.9302；R16同方向大幅恶化。当前固定模型高度依赖与当前场景对应的DSM内容。 | shuffle同时改变空间对应、语义与输入分布，不能唯一归因为像素级correspondence，不能当训练因果消融。 |
| F-CONTEXT-TOPOLOGY | 实验已验证：指定路径与协议内 | T的5个保留上下文配对增益约1.432–1.521pp；模块诊断RGB专家包收益依赖context；Structured同权重naive context却更差11–18pp。 | 不是“打开context一定好”。路径、权重及故障几何共同决定结果；S13在pixel缺失弱于S1。 |
| F-S1-INTERNAL-DSM-FALLBACK | 代码已实现 + 运行回执已验证 | N1.forward对dm & ~rm选dlog；Phase1.5 infer_one逐窗口torch.equal；720个非clean案例全部own_logit_identity.dsm_only=True，2tile×20mask与5/10/25剂量，原载荷SHA已审计。 | 内部S1分支，不是旧D15。未独立GPU复跑/另存完整双份logits；本轮rgb_only可能空支持，不声称其镜像身份已验证。21pp不是能力上限。 |
| F-FIXED-POOL-HEADROOM | 实验已验证：描述性 | 旧五专家oracle−最佳固定R16=10.1103pp。 | 真值oracle非方法，池异构且来源不匹配；两个匹配专家与五专家池变化不可定量归因于单一混杂。 |
| F-BOUNDARY-NOT-DOMINANT | 实验已验证：当前诊断 | ECI1.0205，距离层损伤密度相近。 | 不支持默认优先boundary rescue，也不证明所有边界方法无效。 |

方法设计约束（重写版建议）：保持跨模态坐标对应；允许共位置空间权重、加性残差、availability masking；非共位置替换只允许明确登记的负控制，不默认成为部署操作。上述发现的组合只能作为下一实验约束，不能写成有效融合的普遍充分必要定理。

[Phase1.5原结果](PHASE_1_5_RESULTS_20261013.md)；[T结果](POST_T_FULL_RESULTS_20261011.md)；[模块诊断](POST_T_MECHANISM_RESULTS_20261011.md)；[身份回执审计](../../records/phase2_design_20261013/internal_dsm_identity_audit.json)；[Phase2完整设计](../protocols/PHASE_2_MATCHED_COMPLEMENTARITY_20261013.md)。
