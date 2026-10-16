# D26定向文献与交叉研究映射

检索日期2026-10-02；范围2024—2026。Origin Skill: academic-research-suite；Mode: plan。只采用出版方、作者原文/仓库；定向阅读不是系统综述，未声称复现任何论文。最新不等于最适用，作者结果不移植到本数据。

| 来源/状态 | 实际阅读范围与关键思想 | 对本项目的用法与边界 |
|---|---|---|
| [KTB，CVPR2025](https://openaccess.thecvf.com/content/CVPR2025/html/Cai_Keep_the_Balance_A_Parameter-Efficient_Symmetrical_Framework_for_RGBX_Semantic_CVPR_2025_paper.html)，[作者代码](https://github.com/imcjx/KTB) | 摘要、引言片段、README；两模态适配与稀疏交互 | 支持同时重视两模态。对称结构已经是已有技术；本轮复用异构专家，不冒称KTB复现 |
| [DGL，ICCV2025](https://openaccess.thecvf.com/content/ICCV2025/html/Wei_Boosting_Multimodal_Learning_via_Disentangled_Gradient_Learning_ICCV_2025_paper.html)，[方法](https://arxiv.org/html/2507.10213v1) | 阅读算法/式9–15和RGB-D实验；分离编码器与融合优化 | 梯度幅度受抑与负cos冲突不是同一问题，D25负结果不能否定DGL。作为解释来源；本轮优先固定现有专家检验信息交互，联合适配只作强对照，不再追加投影 |
| [MFFNet，GIScience & Remote Sensing 2025](https://doi.org/10.1080/15481603.2025.2534740) | 出版方摘要及3.1–3.2片段；空间/小波特征与多尺度高频融合 | 小波+RGB/DSM融合已有先例。需与等容量空间表示、打乱对应比较，不能声称Haar本身新颖 |
| [DIS2，WACV2026 Earth Observation Workshop](https://arxiv.org/abs/2601.13502)，[方法全文](https://arxiv.org/html/2601.13502v1) | 元数据标注Workshop接受，方法3.1–3.3及三状态评价；独有/补偿表征及类别贡献 | 应同时评价完整、RGB缺失、DSM缺失。补偿蒸馏是近邻，本轮不同时叠加，以免无法归因 |
| [CBC-SLP，2026预印本](https://arxiv.org/abs/2604.15856) | 摘要与结构化投影式22–27；共享/独有表示与availability路由 | 保留模态特有信息有依据；共享/私有分解不是新贡献。本轮不强制两表征对齐 |
| [SGMA，TGRS2026](https://ieeexplore.ieee.org/document/11517493)，[作者原文](https://arxiv.org/html/2603.02505v1) | 摘要、SGF/MAS描述；多尺度原型与模态采样 | D24简化EMA bank负结果不否定完整SGMA。当前新设计仍须承认语义引导是已有思想 |
| [RGSNet，SSRN2026预印本](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7097142) | 仅作者摘要/元数据；频率证据估计异质退化可靠性 | 最接近的创新边界之一；SAR换DSM或再加语义gate不足以成立新颖性 |
| [传感器故障基准，CVPRW2025](https://openaccess.thecvf.com/content/CVPR2025W/TMM-OpenWorld/html/Liao_Benchmarking_Multi-modal_Semantic_Segmentation_under_Sensor_Failures_Missing_and_Noisy_CVPRW_2025_paper.html) | 官方摘要与缺失/噪声状态划分 | 采用双向整幅/局部缺失与质量变化分开报告，等权开发指标不冒充部署分布 |
| [Zipper，NeurIPS高效语言语音Workshop2024](https://proceedings.mlr.press/v262/zayats24a.html) | 主会外Workshop原始摘要；连接独立塔并保留单模态能力 | 跨领域借鉴私有通路与交互通路分开。语音文本结果不证明遥感有效 |
| [SynIB，2026预印本](https://arxiv.org/abs/2606.09853) | 仅摘要；区分联合信息及单模态信息 | 只借鉴“共同正确/独有正确/双错但融合纠正”的诊断视角。该统计不是严格PID估计；不采用惩罚缺失时自信的目标，避免与单模态能力目标冲突 |

## 本轮要检验的差异

从已有两个真实单模态专家提取可保留的私有表征，学习两个方向的特征增量；在完全相同专家、训练流、头容量下，检验语义依据和频率基是否改善交互。这是**重写版建议/可行性设计**，不是已成立的方法贡献或上述论文的完整复现。

相比D23，改变的是专家信息来源和交互位置；相比MFFNet/RGSNet，潜在差异在双向独有正确保留与明确单模态通路。但这些差异尚不足以单独确立新颖性。若结果仅由普通特征融合或联合适配解释，保留强基线、撤回新机制贡献；只有匹配消融成立后才准备完整近期方法同协议复现。

本轮没有采用近期大模型论文的分数、把Workshop写成主会，或把预印本当已同行评审结果。更详细元数据见[来源表](../../records/research_d26_plan_20261002/literature_sources.json)。
