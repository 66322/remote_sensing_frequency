# 2025—2026语义分割与遥感多模态：定向检索及迁移矩阵

核对日期2026-10-30；证据：一手论文页面、摘要、部分PDF及作者代码入口。本次是问题导向扫描，不是覆盖整个领域的系统综述；没有执行论文代码。论文机制均属“论文已声称”，对本项目的可迁移性均属“重写版建议”。CVF/Xplore部分直接页面有403/验证，本表仅采用实际可读的一手搜索内容、作者页或PDF，不假装已经全文复现。

## 1. 领域并行推进的方向

2025—2026同时研究强表征与简洁分割头、像素空间读出、多尺度上下文、几何先验、缺失/失衡多模态、参数高效适配、跨域蒸馏和开放词汇。不存在由本次证据支持的“领域已经全部告别融合”结论。尤其MM-DINO直接覆盖DINOv3多模态遥感，LiDeRe/AnyUp让浅层头不再是足够的强对照。

| 文献与核实状态 | 已有工作 | 本项目迁移与必须的控制 |
|---|---|---|
| [EoMT](https://github.com/tue-mps/eomt)，CVPR2025 Highlight | ViT图像/查询token统一建模，简化分割结构 | 强分割建模基线；不能把其可训练骨干和大模型效果等同冻结ViT-S浅头 |
| [SegMAN](https://openaccess.thecvf.com/content/CVPR2025/html/Fu_SegMAN_Omni-scale_Context_Modeling_with_State_Space_Models_and_Local_CVPR_2025_paper.html)，CVPR2025 | 局部注意力、状态空间与多尺度上下文 | 真实多尺度/视野基线；固定GSD、物理视野和容量；Mamba名称不是创新 |
| [DFormerv2](https://arxiv.org/abs/2504.04701)，CVPR2025 | 深度几何先验进入注意力 | G路线强近邻；DSM高程与透视深度不同，需要高度单位、相对高差和配准干预 |
| [Keep the Balance](https://openaccess.thecvf.com/content/CVPR2025/papers/Cai_Keep_the_Balance_A_Parameter-Efficient_Symmetrical_Framework_for_RGBX_Semantic_CVPR_2025_paper.pdf)，CVPR2025 | RGB+X对称参数高效适配 | P路线控制模态适配不平衡；室内RGB-D/热红外等结果不直接等于航拍DSM |
| [Rein++](https://arxiv.org/abs/2508.01667)，2025预印本 | 实例token域泛化、另有无标签目标域适应 | 冻结头/LoRA/token控制；DG与UDA分开，代码入口本次未确认可用 |
| [CFCGNet](https://www.sciencedirect.com/science/article/pii/S1566253525002805)，Information Fusion2025，DOI10.1016/j.inffus.2025.103207 | 特征补偿、融合、GCN重构解码 | 说明融合/重构仍在发展；须与普通空间和同容量解码比较 |
| [AMMNet](https://arxiv.org/abs/2507.16158)，2025预印本 | 非对称RGB/DSM编码、模态先验与分布对齐 | 轻量DSM分支/非对称融合近邻；分布对齐不等于已解决空间错配，未核实正式venue |
| [LiDeRe](https://openaccess.thecvf.com/content/CVPR2026/html/Luddecke_LiDeRe_A_Lightweight_Readout_for_Fast_and_Data-Efficient_Dense_Prediction_CVPR_2026_paper.html)，CVPR2026；[代码](https://github.com/timojl/lidere) | 冻结骨干的插值/注意力轻量稠密读出 | S优先强对照；先区分信息不足与读出不足，再谈DSM结构收益 |
| [AnyUp](https://wimmerth.github.io/anyup/)，ICLR2026 Oral；[正式稿](https://openreview.net/pdf?id=Y9UAgPehqo) | RGB引导、特征维度无关的通用上采样 | 先原RGB引导，再DSM结构；固定高分辨率输入可用性，不偷偷增加清晰信息 |
| [Upsample Anything](https://arxiv.org/abs/2511.16301)，CVPR2026 | 无需数据集训练的测试时优化上采样 | 强简单控制；固定优化步数、计推理耗时，禁止用下游开发GT做优化 |
| [GKD](https://arxiv.org/abs/2603.02554)，CVPR2026；[代码](https://github.com/Younger-hua/GKD) | 表示蒸馏与任务适配分阶段，选择可泛化空间知识 | C路线不应只比较普通KL；额外预蒸馏阶段、教师和数据全部计成本 |
| [MM-DINO](https://doi.org/10.1109/TGRS.2026.3677346)，TGRS2026；[代码](https://github.com/KimotaQY/MM-DINO) | DINOv3单/多模态遥感分割、LoRA，覆盖Potsdam/Vaihingen | A/P直接近邻。“DINOv3+DSM+LoRA”不是空白；公开数据集微调权重可能暴露开发数据，不能直接作干净公共初始化；其DSM jpg与本项目浮点DSM须统一 |
| [SGMA](https://arxiv.org/abs/2603.02505)，2026预印本 | 类别原型可靠性、适配融合与模态采样，处理不完整多模态 | Q强近邻；简单entropy/缺失标志和未知局部质量分开。未核实venue，不采纳第三方“CVPR2025”标注 |
| [MIAM](https://proceedings.iclr.cc/paper_files/paper/2026/hash/29536cd0e09e7f27d9eaaed7330f96cb-Abstract-Conference.html)，ICLR2026 | 模态失衡自适应掩码，生态/地理多模态分类 | Q迁移启发；不是RGB–DSM密集分割已验证。固定损伤、等暴露分布/时序控制不可省 |
| [DIS2](https://openaccess.thecvf.com/content/WACV2026W/CV4EO/html/Kieu_DIS2_Disentanglement_Meets_Distillation_with_Classwise_Attention_for_Robust_Remote_WACVW_2026_paper.html)，WACV2026 CV4EO workshop | 解耦、蒸馏与类别注意力 | C近邻，不标为WACV主会；需要普通feature/logit KD、同教师同预算 |
| [MSSDF](https://github.com/CVEO/MSSDF)，Information Fusion2026 | 多模态自监督预训练和融合 | 公开方案包含约64万DOM–DSM对预训练；额外数据不是免费能力，本阶段不默认复刻大预训练 |
| [STARS](https://doi.org/10.1016/j.jag.2026.105378)，JAG151(2026)105378；[预印本](https://arxiv.org/abs/2601.17342) | 共享/特有翻译、stop-gradient非对称对齐、类别均衡像素语义对齐，针对缺失模态 | C近邻。用户贴文将期刊写为Information Fusion不准确；具体模块迁移前仍须全文/代码核对 |
| [CMH-CL](https://github.com/TINYWAI/CMH-CL)，作者代码 | 光学/SAR二分类场景的多模态方法 | 不能直接继承到RGB–DSM六类；须分清传感器、任务和输入缺失设定 |
| [OVS-DINO](https://arxiv.org/abs/2604.08461)，2026预印本 | SAM结构先验、DINO层间边界能力、语言引导 | 可做浅/深特征结构诊断；不为六类全监督任务强加语言，SAM提示不能取外层GT |
| [CrossEarth-Gate](https://arxiv.org/abs/2511.20302)，CVPR2026作者标注；[代码](https://github.com/ShileiCao/CrossEarth-Gate) | 遥感基础模型的跨域/适配方向 | P直接对照范围；访问目标域信息和预训练数据暴露须与本方案分开 |

BATFNet、DLGCNet及SAM对象边界方向已在[10月29日审计](POST_M2_EVIDENCE_AND_LITERATURE_AUDIT_20261029.md)记录；本次没有把所有候选都纳入首批复现成本。首轮机制筛选不等于论文完整SOTA比较，入围后要统一协议复现最近的强方法。

## 2. 用户贴文的核对与修正

| 原主张 | 核对结果及规划处理 |
|---|---|
| 静态融合达到香农互信息物理上限 | D18/D26/D27是有限配方结果，没有条件互信息/Bayes风险估计，不成立 |
| 2025/2026不再做普通融合 | 上表包含当年融合、上下文、解码研究，不能概括为全领域放弃 |
| M2失败证明共享梯度竞争 | M2固定RGB教师、独立DSM训练，未验证共享参数冲突；新底座先测 |
| PCGrad/MTPOA保证已正确像素永不受损 | [PCGrad原论文](https://arxiv.org/abs/2001.06782)是任务梯度处理，不能推出有限步、非线性、逐像素零损伤；[MTPOA条目](https://mail.svedbergopen.com/index.php/ijaiml/article/view/299)不支持本项目保证 |
| EDL自然检测退化、精确区分未知 | 证据量受优化/参数化影响；[ICML2024讨论](https://proceedings.mlr.press/v235/juergens24a.html)与[ICLR2026 Stop Guessing](https://proceedings.iclr.cc/paper_files/paper/2026/hash/55aeba84b402008d3ed10440d906b4e1-Abstract-Conference.html)限制直接不确定性解释。必须对比温度校准/熵和未知损伤真实排序 |
| SENSSE可直接支持RGB–DSM多模态EDL | [PubMed条目](https://pubmed.ncbi.nlm.nih.gov/42879268/)属于不同医疗分割场景；机制可考察，任务保证不能迁移 |
| MIAM评审“迁移遥感可从8到10分” | 正式论文可查；未取得可核对评审证据，不引用该评价或作创新论据 |
| DIS2是WACV主会、STARS是IF | 分别为CV4EO workshop、JAG；不按错误venue评估成熟度 |
| MLDANet+MDI+DALoRA构成确定的最新方案 | 贴文所指精确组合与版本未可靠对应，不据此实现；采用已核对MM-DINO/Keep the Balance/Rein等对照 |
| 教师应带来2–4pp、LoRA避免遗忘、组合一两周顶刊 | 均无本项目证据；训练可运行、增量、机制与发表价值分别验收 |

## 3. 原实验与新问题的对应

历史原报告再核对：D26 XSF−B0=+0.1568289pp，但XSF−简单J0=−0.0023412pp；D27 G1−G0=−1.7686006pp。M2各折DF−D0约−0.000840/−0.001181/−0.001762pp，融合平均变化近零微负，不能描述成巨大精度灾难。D27“救回19.98%”与“伤害4.24%”分母分别为23,478,234和197,573,156，不能直接相减比较净收益。精确数据路径及协议见10月29日审计与各原报告。

原N1多深度使用固定通道压缩与投影尺度，未覆盖原生DINO多层特征；原A0最后层1×1+128标签未覆盖强密集解码。故新S/G可以有实质差别，但仍必须胜过简单高分辨率skip、普通高度距离和匹配解码控制。候选如果只靠换更强头获得收益，结论应归为底座改进，不写成DSM新机制。

## 4. 与论文三章的联系（候选，不承诺）

| 历史章节问题 | 可保留的研究问题 | 尚缺什么证据 |
|---|---|---|
| SR增强分割 | C：受限观测下可迁移的任务信息恢复 | 对普通增强/KD的净分割收益，教师优势及输入可识别性 |
| RGB–DSM交互 | G/Q：几何对应及局部质量变化下的条件互补 | 真实强对照、未知质量、正常区域保护与独立地域 |
| 频率/结构重建 | S：粗表征到边界/小目标的空间读出；频率为条件子问题 | RGB引导及强读出控制、频率独有效应，不能只换算子名称 |

若仅一条问题成立，应围绕成立证据调整论文；不强迫每章都保存旧模块，也不把尚未运行的表格写为贡献。

