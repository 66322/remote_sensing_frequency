# 跳出 RGB–DSM：近期遥感期刊线索与候选实验（2026-10-22）

状态：RESEARCH_ADVICE_NOT_SELECTED_NOT_IMPLEMENTED_NOT_LAUNCHED。本文为重写版建议和代表性文献扫描，不是新执行合同、已验证机制或已采纳的主线变更。

证据基准：GitHub 分支 rebuild-v1-protocol-20260915，读取头 90b9bbe8f4fe4777aa10b11aea48ddd572785a39。当前 M2→J→R→T→V 合并队列已实现、尚未运行；本轮无服务器查询、数据下载、任务登记或训练，未改变执行源码、作业数、顺序和门禁。

## 1. 本轮判断及与之前建议的区别

用户最新要求参考遥感期刊研究方向，主动考虑 RGB–DSM 以外的实验。用户仍以研究问题和创新性为先，无期限压力，可下载公开数据。对此，助手建议从“优先留在几何辅助分割里换解法”拓宽为“保留既定诊断，同时独立论证至少一个新任务或新决策问题”。理由是任务、监督来源和部署条件的变化可能带来更清楚的研究对象；不要求 M2 先失败才能开展新方向可行性研究。

这属于助手建议，用户尚未选择具体新主线。已授权合并队列照原合同保留；下列方向没有自动追加进队列。T（高度变化）与 V（建筑对象）已经在队列中，不把它们重复包装为本次新增方向。

当前证据支持的是特定机制应收口，而非 RGB–DSM 整个领域失败。[M1归档验收](PHASE3_M1_ACCEPTANCE_AND_ROUTE_REVIEW_20261015.md)表明统一高度幅度没有稳定增加可利用互补；M2 还没有结果。继续投入同一数据上的小模块组合，可能重复遇到“单项指标改善但机制贡献不清楚”的问题，这是路线风险判断，不是对未运行实验的预判。

建议顺序：

1. **新任务首选：旧地图与当期影像的更新，关注错误保留和错误修改之间的权衡。**
2. **低转换成本的独立候选：跨地区部署时，有限标注应该分配在哪里。**
3. **更换观测领域的候选：异步 SAR–光学观测下，指定时刻的灾害水域制图。**
4. 作物时序跨年识别、定量植被反演作为较远备选；结构/矢量输出先利用现有 V 补强基线。

优先级来自现有积累、可检验性和数据条件的综合判断，不表示已证明新颖性，也不保证投稿结果。

## 2. 期刊正在研究什么：代表性证据，不作热度排名

检索日期为2026-10-22，重点核对2024—2026年 RSE、ISPRS JPRS、IEEE TGRS 的出版社页面、作者机构论文及官方代码/数据。以下是与本项目有关的方向样本，不是完整计量综述，不能据此给出领域发表占比或声称某方向最热门。

| 主题 | 核验到的期刊证据 | 对本项目的含义 |
|---|---|---|
| 时间序列与持续监测 | RSE 2025 时间序列特刊前言涵盖不规则观测、变化、参数反演和灾害，并讨论业务化时间序列产品。[S1] | 时间过程与决策时机可以成为研究对象，任务不必固定为单景分割。 |
| 旧图、弱标签与更新 | ISPRS 2024 CMPANet 已研究地图—影像变化；2025 CTS-WS 已研究时空不同步标签。[S2–S3] | 旧地图更新是可用入口；普通跨模态融合和伪标签清洗已有直接先例。 |
| 基础模型的迁移与低标注应用 | ISPRS 2025 GeoSA-BaSA 已用 DINOv2 做跨域分割；RSE 2025 SAMSR 结合时序 SAR、迁移和主动学习开展森林扰动制图。[S4–S5] | 基础模型可作工具与强基线，研究问题应落在负迁移、标注配置或实际监测上。 |
| 灾害制图与真实观测条件 | RSE 2025 研究洪水模型跨数据集泛化；ISPRS 2026 SMAGNet 已处理不完整光学辅助 SAR。[S6–S7] | 把 DSM 换成 SAR 再做缺失门控不足以建立新意；需要更具体的时间/事件/标签合同。 |
| 开放词汇与类别体系 | ISPRS 2025 TACOSS 研究可迁移地物语义；2026 KG-OVRSeg 已处理语义歧义与层次关系。[S8–S9] | 文本提示与知识图谱都不是空白，应检验分类体系转换的一致性和拒识。 |
| 物理量与跨场景可信度 | RSE 2025 叶性状混合建模融合神经网络与辐射传输；2026 草地生物量研究比较模型的跨样地迁移。[S10–S11] | 还可从分类转向定量反演，但须建立测量真值、单位和适用范围，不能只换回归头。 |

这些论文共同提示一个适合本项目的工作原则：先明确哪一种遥感观测或制图需求尚有可改善误差，再选择模型。这个原则是本报告的综合判断，不是期刊统一的录用标准。

## 3. 候选 A：旧地图更新——先前标签在哪里仍可信

### 问题与可移植方法

旧地图既有价值，也会过时。当前影像和旧图不一致时，原因可能是真实变化、旧图边界问题、观测遮挡或类别定义差异。候选问题为：在固定当期标注预算下，能否更少保留过时信息，同时更少误改正确地图？

可借鉴结构化标签噪声建模、稳健估计中的外点状态，以及地图维护中的“保留/修改/待确认”决策。这里尚未指定一个已成立的新方法；直接移植首先作为对照。学习的对象应是旧图证据的适用性及当前变化，而不能仅把两个输入的置信度再混合一次。

### 两种可选合同，先选一个

**A1 地图—影像变化候选。** [EVLab-CMCD作者仓库](https://github.com/whudk/EVLab-CMCD)当前 README 使用 EVLab-SHPCD 名称，提供旧土地利用图、当前影像和新增开发地二值标签。只能据此研究新增开发地，不扩写成所有土地利用转移。先确认原始地理分组、许可和标签范围；随机patch划分不能代替跨地区验证。

同输入强对照包括：当前影像模型；当前影像预测后与旧图规则比较；旧图和当前影像普通拼接；常规配准后比较；CMPANet；候选的旧图有效性处理。若当前影像独立语义预测需要额外语义标注，必须另列额外监督参照，不能假装与仅变化标签的模型公平。

主评价可用变化区域精度/召回、对象级新增地召回、每平方公里误报和固定核查对象数下的召回。对象连接和匹配规则需预先固定。先审查真实误报是否确由旧图问题产生；合成错位、置空/打乱旧图仅作为机制干预。没有独立错误类型标注时，不能声称已准确识别真实错位或过时原因。

**A2 少新标签的时序地图维护。** [DynamicEarthNet原论文](https://openaccess.thecvf.com/content/CVPR2022/papers/Toker_DynamicEarthNet_Daily_Multi-Spectral_Satellite_Dataset_for_Semantic_Change_Segmentation_CVPR_2022_paper.pdf)提供跨AOI时序影像与月级语义标签，可在开发区域内将首期标签作为旧图，按预算开放后续标签，分别统计稳定区域和真实转变区域。以最新一期地图生成或修订为目标，比较旧图沿用、少量当期监督、全旧标签训练、简单变化过滤、标准自训练，以及适配输入合同后的 CTS-WS 对照。

A2须先锁定旧图月份、目标月份、影像可用截止时间、可查询标签预算和独立选模区域；未开放的当期/未来标签不得参与选样或选模。

A1 与 A2 的输入、标注和目标不同，不能合并排名；一个成立不自动证明另一个成立。第一轮不同时把标注选择、时间停止、空间配准和所有噪声类型装进一个模型。

### 可以进一步研究的时间决策

若 A2 有稳定可改善残差，可再研究“等待更多证据是否值得”。借鉴序贯检测和最优停止，比较固定窗口、连续k期确认、简单置信阈值与候选策略，在相同误更新率下比较变化召回、按月更新延迟和反复翻转。

CAIM-Net 已研究变化时刻与范围的联合推断[S12]；时间建模本身不新。完整序列模型和只见过去的模型访问的信息不同，必须分开报告。

DynamicEarthNet 含时序补全，可能使用相邻甚至未来观测；SpaceNet7 为月度镶嵌。即使代码只输入前缀，也不能自动证明真实在线性。首阶段只能称月度产品前缀的回顾性模拟；真实在线主张需要核验原始采集时间、产品可用时间和因果预处理。月标签不能当日级事件真值。

### 去留条件

若普通自训练、变化过滤或配准已达到相同预算下的错误保留—错误修改前沿，则停止复杂扩展。若优势只见于人为错位、额外监督或较晚决策，先解释这些因素。只有跨地理开发组重复改善，且不靠抹除真实变化或拒绝所有困难区域取得收益，才进入完整方法研究。

## 4. 候选 B：固定标注预算，应该把样本分配到哪里

### 问题与首轮实验

跨地区推广时，最不确定的样本可能集中在同一地区、重复纹理或标签歧义处。可问：有限标注的收益主要受模型不确定性、地理覆盖还是样本冗余影响？这是数据获取与实验设计问题，可以完全不用 DSM。

用 [OpenEarthMap官方项目](https://www.open-earth-map.org/)的地区及来源信息构建开发实验；后续可用 FLAIR 检验迁移。OEM 来自多个既有影像源，需按地区、坐标及原始来源查重；不能把其已有来源子集重新称为独立外部集。

固定一个公开编码器与分割头，先比较随机、预测熵、特征k-center、地理分层随机和一个结合相关性/覆盖度的候选。至少两个预定标注预算，按独立地区汇总学习曲线、稀有类表现和最差地区表现。所有方法使用同样的初始标注、可查询样本池、训练预算与停止规则。

必须分清两种合同：从源地区选标注后向新地区泛化，和允许在部署地区的独立样本池购买少量标签。后者是带目标监督的适配，不能称零标签域泛化。无论哪种合同，最终评估区域与查询池独立；未查询标签不得参与选样、阈值或类别平衡。先按固定面积/地块计预算；没有人工计时实验时不声称节省某百分比的标注工时。

### 方法机会与去留

可借鉴最优实验设计、批量主动学习和相关样本的信息增益。它们本身及其遥感应用已有研究，[SAMSR](https://doi.org/10.1016/j.rse.2025.114775)与TGRS的共形主动学习[S13]也说明方向已发展。需要检验的具体增量是：在地理相关、稀有类和分布迁移共同存在时，候选是否比简单覆盖策略稳定有效。

若地理分层随机或k-center等效，就停止复杂采样设计。若只是使用了更多地区或更多标签，不能归因于算法；应在相同预算和可用信息下比较。基础模型适配器不宜和新选样器同时替换，否则难以解释收益。

## 5. 候选 C：异步 SAR–光学观测下的指定时刻水域制图

### 问题与数据条件

洪水会随时间变化。两种传感器的影像不同步时，光学信息可能很清晰，却描述了另一个水域状态。这个问题不同于“辅助模态质量低”。

先固定目标为 SAR 拍摄时刻的水域状态，光学为辅助信息。[C2S-MS官方说明](https://radiantearth.blob.core.windows.net/mlhub/c2smsfloods/Documentation.pdf)包含近同时相的SAR/光学对、各自水标签及光学云/云影标注；[公开入口](https://registry.opendata.aws/c2smsfloods/)。是否有足够时间差和独立事件支持该问题，必须先核验元数据分布。

还须核对各模态标签对应的时刻和生成方式；若标签只反映传感器可见性，不能把它直接当独立的真实水域状态测量。

两模态标签分歧也可能来自可见性、配准或标注口径，不能直接充当真实洪水演化真值。时间差可能与地区、事件阶段和传感器条件混杂，分层相关性不等于因果效应。

水域标签包含永久水体；没有灾前水体/事件变化真值时应称事件期间水域制图，不能直接宣称识别洪水新增淹没，更不能称风险预测或洪灾预报。

### 对照与跨领域迁移

按事件与地区隔离开发，比较 SAR-only、普通拼接、[SMAGNet官方实现](https://github.com/ASUcicilab/SMAGNet)、时间差标量条件化、简单时间阈值回退和候选状态更新。[RSE跨数据研究的官方模型](https://github.com/kipoju/udl4fl)是另一强参照。所有臂看到相同时间/有效性元数据；多数据训练来源要去重事件。

可借鉴异步传感器状态估计，分别表示当前状态证据和历史证据。第一版只检验时间信息是否提供超越简单回退的价值；不在两张近时相图上声称恢复完整洪水动力学。真实标签一致性仅离线诊断，不能作为推理门控输入。

报告每事件水域精度、漏检/误报、自然云区域表现及不同时间差下的结果。若进一步做待复核区域排序，应固定复核面积预算、同时报告保留区域漏检和总覆盖；空间相关与跨事件漂移下不照搬独立同分布风险保证。

### 去留条件

时间差缺乏变化、独立事件不足或标签误差无法区分时，不推进“时间错配”主张，可保留普通跨事件制图评估。若复杂模型不能优于SAR-only、时间阈值回退及SMAGNet，或收益只来自更多训练事件，就关闭该机制。避免把这一路线做成旧RGB–DSM门控的传感器替换版。

## 6. 其他方向的角色

- **作物跨年时序识别：** 可问物候阶段变化与作物类别/比例变化能否区分，使用[Sen4AgriNet作者库](https://github.com/Orion-AI-Lab/S4A)核验跨年/跨地区开发划分。TimeMatch、无源域适配[S14]、RAINCOAT-SRS[S15]已覆盖普通时间对齐与迁移。可借鉴部分匹配和标签偏移建模，但先比较日期增强、简单时间平移与类别先验校正。此方向是真正任务转换，需理解作物标签和农时，不把PASTIS常用划分自动称跨年验证。
- **定量植被/生物量反演：** 是比语义分割更远的选择。可从物理模型残差学习、样地到像素支持差异、跨地区不确定性切入[S10–S11]。两张GPU不是唯一约束，独立样地测量、时间匹配、单位和物理知识更关键。先选一种变量与可核对真值，不直接把分类网络换回归头当新路线。
- **建筑/道路的结构和矢量输出：** 已有V邻近探索，应补[SAMPolyBuild](https://doi.org/10.1016/j.isprsjprs.2024.09.018)、[PolyR-CNN](https://doi.org/10.1016/j.isprsjprs.2024.10.006)等成熟对照。转道路还需真实道路图，不能用不透水面语义标签替代道路连通真值。
- **开放词汇与分类体系转换：** 将TACOSS、KG-OVRSeg和SegEarth-OV列为最近邻与基线候选；本轮回读KG-OVRSeg官方仓库仍显示源码待整理发布，不能当作已可直接运行。可以研究合法类别映射、同义词扰动和拒识，但不能仅增加提示词或知识图谱。基础模型预训练重叠未知时，只称监督微调未见地区，不称模型从未见过该地区。
- **生成/去云/超分：** 保留为任务需要时的工具。RSE 2026 G2R 已直接讨论异日影像作为真值的时序问题[S16]；“去云后图像更好看”与变化/定量任务改善需分开验证。恢复仍不因热点升级为本项目主线。

## 7. 怎样开展，避免又变成数月盲目搜索

建议先给A/B/C各做一次资料与基线可行性核验，随后只选择一条独立新方向进入长程实验；这一建议不取消、暂停或改排既定队列。

每个候选先交付：真实失败样本、输入与标签合同、成熟基线、可迁移方法的最小实现想法，以及能否定该方法的比较。合适的首轮通常为4—6个有解释作用的对照、少数预定地理/事件开发组和固定标注预算，重复数与停止阈值在看候选结果前另行登记。这里没有自动新增seed或训练作业。

进入长程验证后，计算量应投入跨地区/跨年/跨事件、强基线复现、机制消融、标签预算曲线和失效边界。不同数据的步数不等于同样耗时，须先测吞吐与显存，再制定预算。时间充裕允许更完整的验证，不要求把每个候选都跑成大队列。

去留依据是：现实问题存在；简单方法仍有残差；候选改善超过额外信息/容量/预算解释；跨条件重复；正常条件和代价可接受。阴性机制结果也应完整保存，但不能自动保证组成可发表论文。

本轮不访问旧Val2/Test6/held4/final或新数据公开test，不查询服务器实时状态，不下载大数据、不启动训练。所有未来服务器原件仍在/home/jovyan/zzx独立目录，由用户终端执行。

## 8. 来源清单与核验限制

检索使用任务词与期刊名组合，如“RSE 2025 time series”“ISPRS weak supervision outdated labels”“flood Sentinel-1 Sentinel-2 generalization”“vision foundation model domain generalization”“active learning geographic”。根据出版社页、作者机构原文与官方仓库核对题名、年份、任务及公开入口；未使用论文自报SOTA作为跨文献公平结论。部分出版社正文访问受限，因此方法深层细节和最终创新边界还须在选定方向后逐篇复核。未下载数据验包，未复现任何外部结果。AI辅助检索与综合，事实与助手推荐在正文中分开。

- [S1] Zhang et al. (2025). Preface: Advancing deep learning for remote sensing time series data analysis. RSE 322, 114711. [DOI](https://doi.org/10.1016/j.rse.2025.114711)，[作者机构记录](https://hub.hku.hk/handle/10722/369665)。
- [S2] Deng et al. (2024). Cross-modal change detection using historical land use maps and current remote sensing images. ISPRS JPRS 218, 114–132. [DOI](https://doi.org/10.1016/j.isprsjprs.2024.10.010)。
- [S3] Zhao et al. (2025). A cross-spatiotemporal weakly supervised framework for land cover classification: Generating temporally and spatially consistent land cover maps. ISPRS JPRS 227, 519–538. [DOI](https://doi.org/10.1016/j.isprsjprs.2025.06.005)。
- [S4] Luo et al. (2025). Domain generalization for semantic segmentation of remote sensing images via vision foundation model fine-tuning. ISPRS JPRS 230, 126–146. [DOI](https://doi.org/10.1016/j.isprsjprs.2025.09.004)，[官方代码](https://github.com/mmmll23/GeoSA-BaSA)。
- [S5] Tian et al. (2025). A vision foundation model-based method for large-scale forest disturbance mapping using time series Sentinel-1 SAR data. RSE 325, 114775. [DOI](https://doi.org/10.1016/j.rse.2025.114775)。
- [S6] Portalés-Julià et al. (2025). Understanding flood detection models across Sentinel-1 and Sentinel-2 modalities and benchmark datasets. RSE 328, 114882. [DOI](https://doi.org/10.1016/j.rse.2025.114882)。
- [S7] Lee & Li (2026). A Spatially Masked Adaptive Gated Network for multimodal post-flood water extent mapping using SAR and incomplete multispectral data. ISPRS JPRS 232, 492–508. [DOI](https://doi.org/10.1016/j.isprsjprs.2025.12.023)。
- [S8] Zermatten et al. (2025). Learning transferable land cover semantics for open vocabulary interactions with remote sensing images. ISPRS JPRS 220, 621–636. [DOI](https://doi.org/10.1016/j.isprsjprs.2025.01.006)。
- [S9] Reducing semantic ambiguity in open-vocabulary remote sensing image segmentation via knowledge graph-enhanced class representations. ISPRS JPRS (2026). [DOI](https://doi.org/10.1016/j.isprsjprs.2025.11.029)。
- [S10] Sun et al. (2025). Hybrid modelling of leaf traits: Integrating neural networks with radiative transfer theory. RSE 329, 114958. [DOI](https://doi.org/10.1016/j.rse.2025.114958)。
- [S11] Schweizer et al. (2026). Testing the accuracy and transferability of remotely sensed biomass models across heterogeneous grasslands. RSE 335, 115294. [DOI](https://doi.org/10.1016/j.rse.2026.115294)。
- [S12] Li et al. (2026). Information transmission: Inferring change area from change moment in time series remote sensing images. ISPRS JPRS 231. [DOI](https://doi.org/10.1016/j.isprsjprs.2025.10.032)，[官方代码](https://github.com/lijialu144/CAIM-Net)。
- [S13] Assessing Conformal Prediction for Remote Sensing: Application to Local Climate Zone Classification. TGRS 64 (2026). [DOI](https://doi.org/10.1109/TGRS.2026.3719780)。
- [S14] Mohammadi et al. (2024). A source-free unsupervised domain adaptation method for cross-regional and cross-time crop mapping from satellite image time series. RSE 314, 114385. [DOI](https://doi.org/10.1016/j.rse.2024.114385)。
- [S15] Gackstetter et al. (2025). Self-attention and frequency-augmentation for unsupervised domain adaptation in satellite image-based time series classification. ISPRS JPRS 224. [DOI](https://doi.org/10.1016/j.isprsjprs.2025.03.024)。
- [S16] Zhang et al. (2026). Cloud removal in remote sensing images using the G2R framework and SSMamba. RSE 337, 115321. [DOI](https://doi.org/10.1016/j.rse.2026.115321)。

文献支持研究主题和最近邻存在，不能替代本项目的新颖性验证、实际数据核验或实验结果。
