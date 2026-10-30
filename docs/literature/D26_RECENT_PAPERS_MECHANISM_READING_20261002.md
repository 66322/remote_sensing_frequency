# 近期论文定向阅读：双向互补、缺失补偿与频率机制
检索/阅读日期：2026-10-02。研究范围：2024—2026；以2025—2026工作为主。Origin skill: literature-review。性质为定向机制阅读，不是系统综述或方法复现；未统计引用量，未引用他人实验数值作为本项目收益。

## 当前问题与结论边界
当前主问题保持：RGB外观/纹理/语义与DSM高度/几何的双方互补，以及任一模态退化/缺失时的可靠分割。D26九组固定计划继续，文献阅读不改变预算、阈值、执行代码或选模规则，不启动新队列。最后共享运行观测仍为19:18，不能由阅读推断服务器实时状态。
已有D15—D25结论见[汇总](../experiments/RESEARCH_SYNTHESIS_D15_D25_20261002.md)：DSM具有独立类别信息、RGB退化时存在互补，last4/质量增强应作为强基线，缺失训练存在完整精度取舍；旧gate/原型/KD/分头/投影的具体机制未过预设门槛。以上不是整个频率、语义或补偿问题被否定。
当前D26固定单模态回退的恒等关系只能保证复用专家；在该回退路径上，冻结组不能学习出高于原专家的全缺失精度。若之后以缺失状态新增能力为目标，需另设可学习补偿路径，不能把恒等回退算作学习贡献。

## 最值得阅读的来源与实验映射
| 来源、状态、实际阅读范围 | 论文机制 | 可借鉴的具体问题与边界 |
|---|---|---|
| [Keep the Balance / KTB，CVPR2025](https://openaccess.thecvf.com/content/CVPR2025/papers/Cai_Keep_the_Balance_A_Parameter-Efficient_Symmetrical_Framework_for_RGBX_Semantic_CVPR_2025_paper.pdf)，Cai等；官方检索抽取的摘要、引言，不宣称阅读全文 | 同时适配RGB与X，动态稀疏交互，以准确双模态预测指导单模态 | 强化双方独立表示的设计依据。D26使用异构历史专家，不是KTB完整复现；“双向/对称”本身已有先例。后续近邻对照应在匹配协议下实现，不能直接比论文表中分数 |
| [DIS2，2026，WACV Earth Observation Workshop](https://arxiv.org/abs/2601.13502)，Kieu等；元数据及方法3.1—3.3 | 分离模态Distinct与Supplement分支，以完整融合特征/logits蒸馏缺失补偿，结合类别及多分辨率信息 | 与RGB/DSM问题最贴近；输入为RGIR/NDSM，并不与本项目RGB/DSM完全相同。建议优先考虑“保留独有信息+任务补偿残差”，而不是强迫全部特征一致或重建完整DSM。D24普通/纠错区域光学KD不是该方法的完整复现，旧负结果不能否定它 |
| [SGMA，2026作者原文](https://arxiv.org/html/2603.02505v1)；方法III-A—III-C与摘要。此轮按arXiv来源引用，不重新声称已核验期刊状态 | 全局类别语义、像素查询、可靠性融合和模态感知采样联合处理不完整输入 | 学到的是“类别、像素、状态”的可靠性，而不只是一个全局模态权重。不能将D24简化EMA原型bank等同SGMA；也不能直接将熵小当可信，需训练区校准、错误自信诊断与容量对照 |
| [Reducing Unimodal Bias with Multi-Scale Functional Entropy Regularization，ICCV2025](https://arxiv.org/html/2505.06635v1)，Zheng等；方法3.1公式1—4及3.2，官方会议PDF元数据 | 用functional Fisher/entropy代理正则作用于多尺度特征与预测，缓解单模态主导 | 输入/特征敏感性与参数梯度负cos是不同诊断；D25投影失败不能否定模态依赖问题。但论文上界及代理不能等同实际任务信息增加，不能盲目平均双方贡献或鼓励依赖噪声；代码、数值稳定性和真实贡献需核验 |
| [MFFNet，GIScience & Remote Sensing2025](https://doi.org/10.1080/15481603.2025.2534740)，Li等；出版方摘要、架构片段 | 空间与DWT小波特征结合，跨模态及多尺度高频融合 | 是频率双模态方法的直接近邻。小波+融合已非新颖组合。D26空间/频率同容量与错位对照应回答频率基是否增加任务收益；普通空间交互追平时不保留频率贡献 |
| [FDAM，ICCV2025](https://arxiv.org/html/2507.12006v4)，Chen、Gu、Fu；摘要及方法3.1 | 注意力反转与动态频率缩放，针对ViT频率衰减 | 比再次附加Haar模块更明确的“交互之前是否已经丢失边界”假设。该工作主要为稠密预测，不是RGB–DSM缺失模型。若以后采用，需两路/单路和普通残差匹配对照；原文纯attention的分析不能直接外推整个DINO残差网络 |
| [Enhance-then-Balance / EBMC，CVPR2026](https://openaccess.thecvf.com/content/CVPR2026/papers/He_Enhance-then-Balance_Modality_Collaboration_for_Robust_Multimodal_Sentiment_Analysis_CVPR_2026_paper.pdf)，He等；官方元数据、[作者方法3.2—3.4](https://arxiv.org/html/2604.12518v1) | 共享/特有表示、单模态任务保持、跨模态增强，然后能量协调和信任蒸馏 | 情感分析的交叉参考。“表征充分性”应与“优化失衡”分开；不能因DSM总体较弱就认定它在每个类别都应被加强。本项目建议只借鉴保留单模态能力和分阶段比较，暂不同时堆叠四模块 |
| [SynIB，2026预印本](https://arxiv.org/abs/2606.09853)；摘要及目标说明 | 为学习协同信息，准确全模态预测，同时惩罚移除一模态后仍自信 | 借鉴联合信息与单模态信息的区分。其目标可能与本项目缺失时仍可靠预测冲突，不直接移植loss；独有正确/双错纠正计数不是严格PID或理论协同信息估计 |
| [传感器故障基准，CVPR Workshops2025](https://openaccess.thecvf.com/content/CVPR2025W/TMM-OpenWorld/html/Liao_Benchmarking_Multi-modal_Semantic_Segmentation_under_Sensor_Failures_Missing_and_Noisy_CVPRW_2025_paper.html)，Liao等；官方摘要/场景定义 | 整幅缺失、随机缺失、噪声分开，并区别等概率与独立故障分布 | 当前完整/质量退化/全缺失/局部缺失分开报告有依据。合成等权开发分数不冒充实际部署分布 |

FreqFusion [TPAMI2024作者原文](https://arxiv.org/abs/2408.12879)亦复核摘要：低通增强类内一致性，高通恢复边界并用重采样纠偏。它是已有基础算子，不能把直接移植当新贡献；高频既可能是边界也可能是噪声，应通过真实任务收益判断。

## 本次形成的研究判断（助手建议，未采纳新实验）
1. **优先问题是独有信息保留与有用交互。** RGB整体强不等于DSM没有独有正确区域，DSM建筑强也不等于RGB建筑信息无用。先看D26的only-R/only-D保留、rescue/harm、双方退化族和逐tile结果，而非只看综合均值。
2. **缺失回退与缺失补偿应明确分开。** 回退等于已有专家是工程保护；补偿在剩余模态中学到可迁移任务线索才可能改善精度。借鉴DIS2，但要允许不存在可推断信息，不要求凭空还原唯一真实高度/颜色。
3. **频率应回答物理或表征问题。** RGB高频包含纹理/边界，DSM高频包含高度变化/噪声/配准伪影；高频量大不等于可靠。类别内部、目标边界、错位和噪声必须分开解释。FDAM提供“编码阶段频率衰减”新假设，尚未在我们的模型中验证。
4. **先证明瓶颈再采用平衡正则。** D25多数采样梯度同向使全局冲突解释变弱，但不等于无单模态主导。敏感性、梯度方向、信息独有性、置信度校准四者不能混用。

## D26之后的条件选择，不自动加实验
- X/XS/XF/XSF有超过B0、CAP且受保护的收益：只确认有证据的一项，并准备同协议最近邻方法及新seed/独立来源；不把F/S都写成贡献。
- 普通X有效而S/F无独立增量：保留双方互补研究问题，撤回本轮S/F机制承诺。
- 全模态交互有效，主要缺口在缺失：优先准备“独有通路+双向任务补偿残差”小矩阵，比较原专家回退、等容量无KD、普通全域KD、补偿分支；所有组同缺失增强与教师绑定，RGB缺失/DSM缺失分别验收。具体预算阈值需看D26证据后另立，不混入当前队列。
- 主要错误集中边界且频率证据充分：再考虑编码阶段或解码阶段的频率保持，分别作用RGB/DSM并设置空间匹配对照。仅谱图变化不能作为继续条件。
- J0普通适配解释全部收益：保留强基线；不靠追加“平衡/语义/频率”名称维持新方法贡献。

## 检索方法与局限
搜索关键词包括RGB-X segmentation missing modalities balanced learning、RGB DSM frequency segmentation、functional entropy regularization、DIS2、KTB、Enhance-then-Balance、FDAM与Synergistic Information Bottleneck。从CVF会议原文、arXiv作者全文、出版方及作者仓库交叉发现/核对；本机parallel-cli未安装，使用可用web检索工具，不为本次阅读新增认证或安装。部分CVF直接打开返回403，采用官方搜索抽取与作者arXiv方法，不冒称全文阅读。未以二手导读证实技术机制；无引用排名或穷尽性承诺。元数据已由原始页面核对，未做完整BibTeX/DOI批量验证，本记录用于研究规划而非最终参考文献表。
