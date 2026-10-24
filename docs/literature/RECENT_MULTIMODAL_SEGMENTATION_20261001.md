# 近期文献如何指导下一实验

检索截止：2026-10-01；记录时间：2026-10-01 20:32（Asia/Shanghai）。来源：用户明确提出实验应参考最新论文、可借鉴他人思想。本记录是围绕已观察失败模式的定向检索，不是穷尽性系统综述；没有新增服务器观测或训练。检索重点为2025—2026年的遥感不完整多模态分割、模态负迁移、任务收益约束和退化可靠性。方法判断优先使用作者原文、出版方和官方代码，第三方笔记只作发现线索。

## 先明确我们要解决什么

问题主线仍为：光学可用时，如何保留DSM的有益贡献、抑制质量变化导致的有害融合，并支持DSM退化/缺失推理。频率、语义和门控都是可去留的解法。当前不承诺任意模态缺失，也不把C1恢复旁支升级为主线。

[已上传D23 TSF/T0阶段结果](../experiments/D23_TSF_T0_PARTIAL_RESULTS_20261001.md)显示：Potsdam Val2、NoBoundary fg5、既定综合口径下，TSF相对M0_safe−0.148998pp，相对T0仅+0.001578pp；harm减少56.396%，rescue保留62.557%。主要候选TSF已不满足原确认门槛。这支持“门控当前丢失有益纠错”的观察，但不能单凭两组证明频率无效、表示必须解冻或整个问题失败。以下推断均属**重写版建议**，不是实验已验证。

## 六篇直接相关文献及证据范围

### 1. SGMA：类别语义与模态学习平衡

Lekang Wen, Liang Liao, Jing Xiao, Mi Wang. *SGMA: Semantic-Guided Modality-Aware Segmentation for Remote Sensing With Incomplete Multimodal Data*. IEEE TGRS, 64, 2026；出版方标记2026-05-13；DOI 10.1109/TGRS.2026.3692798。**不是CVPR2025论文**。

原方法以类别语义原型参与融合并估计模态鲁棒性，再据此调整采样以加强脆弱模态学习。我们可借鉴“类别相关的可靠性”和“改变训练暴露”，不能把特征相似度直接当作真实任务收益。已有D23的S特征输入并不等价于该方法。真正的损坏DSM也不应因为“脆弱”便无条件提高训练权重。

核对范围：作者arXiv方法节、IEEE元数据、官方仓库README；未复现。出版方摘要称代码/模型可用，而当前查到的作者README仍写Coming Soon，仅见README，不能把完整实现已获取作为执行前提。

来源：[出版方](https://ieeexplore.ieee.org/document/11517493)；[作者原文](https://arxiv.org/html/2603.02505v1)；[官方仓库](https://github.com/wenlk3/SGMA)。

### 2. SimMLM：用任务误差约束模态收益

Sijie Li, Chen Chen, Jungong Han. *SimMLM: A Simple Framework for Multi-modal Learning with Missing Modality*. ICCV2025, pp.24068–24077。

其动态专家混合配合More vs. Fewer（MoFe）损失，比较同一样本更多/更少模态时的任务损失，惩罚增加模态后误差变大的情况。这比仅比较预测置信度更贴近任务目标。实验涉及医学分割及分类，不能直接移植其增益到遥感。

我们优先借鉴配对任务约束；对严重损坏DSM不能无条件要求“模态越多越好”。训练损失下降也不数学保证mIoU单调提高。原MoFe可作为公开思想对照；加该损失本身不构成新贡献。

核对范围：CVF正式元数据、作者原文方法节/式(3)(4)及实验设置；未复现。

来源：[CVF正式记录](https://openaccess.thecvf.com/content/ICCV2025/html/Li_SimMLM_A_Simple_Framework_for_Multi-modal_Learning_with_Missing_Modality_ICCV_2025_paper.html)；[作者原文](https://arxiv.org/html/2507.19264v1)。

### 3. STARS：缺失模态的知识进入可用模态表示

Tong Wang等. *STARS: Shared-specific Translation and Alignment for missing-modality Remote Sensing Semantic Segmentation*. arXiv:2601.17342，2026-01-24。当前核到的是**预印本**，不自行指定已录用会议/期刊。

原文使用共享/特有表示、带stop-gradient的跨模态翻译及像素语义对齐，研究缺失模态时的表示学习，并含Potsdam光学+nDSM训练、仅光学推理。它提示：缺失时除了固定退回R0，还可检验可用分支是否真正学到辅助知识。全域对齐可能损失模态特有信息，不能机械照搬。

核对范围：作者方法节及Potsdam设置；未复现。其光学用IRRG，且划分描述存在需向作者澄清的数量表述，不能直接把表中分数与我们的Val2、RGB/光学通道及NoBoundary口径并排比较。

来源：[作者原文](https://arxiv.org/html/2601.17342v1)。

### 4. PNDC：正负影响区域校准

Yansheng Qiu, Kui Jiang, Hongdou Yao, Zheng Wang, Shin’ichi Satoh. *Does Adding a Modality Really Make Positive Impacts in Incomplete Multi-Modal Brain Tumor Segmentation?* IEEE TMI 44(5), 2194–2205, 2025；DOI 10.1109/TMI.2025.3526818。

原文摘要提出按模态的负影响区域和可靠融合区域进行双向校准。借鉴价值是把“有益与有害区域”用于训练，而不只报告整体mIoU。D23已存在效用标签，不能将重新命名效用监督算作新机制。

核对范围：索引所载作者摘要与官方train_PNDC.py中区域掩码/损失调用的局部阅读；没有取得并精读出版版全部方法，也没有完成代码复现。医学任务的实现、阈值和效果不能直接迁移到DSM。

来源：[作者摘要与正式书目信息](https://pubmed.ncbi.nlm.nih.gov/40031068/)；[官方实现](https://github.com/yansheng-qiu/PNDC)。

### 5. RGSNet：频率与退化可靠性的最近邻思想

Mengru Hou, Guowei Su, Tian Qiu, Wenhao Zang, Luobing Dong. *Reliability-guided SAR-Optical segmentation under heterogeneous degradation*. SSRN，2026-07-11；DOI 10.2139/ssrn.7097142。**作者预印本，未核到同行评审录用状态。**

摘要已提出从频率证据构建退化敏感可靠性代理，再做选择性子带修正与融合，与“频率＋可靠性＋退化”组合高度接近。不能再仅凭这个组合宣称创新。SAR散斑/光学云与DSM高程误差的成因不同；真实建筑边界也含高频，不能直接把高频判成坏信息。

核对范围：SSRN可检索的作者摘要与发布日期；正文页面访问失败，未精读25页全文、未验证实现或复现。作为必须继续核清的最近邻，不作为已验证可移植算法。

来源：[作者预印本记录](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7097142)。

### 6. 传感器故障分割基准：能力应分开评价

Chenfei Liao等. *Benchmarking Multi-modal Semantic Segmentation under Sensor Failures: Missing and Noisy Modality Robustness*. CVPR2025 **TMM-OpenWorld Workshop**，arXiv:2503.18445。

其评价区分整模态缺失、随机缺失、噪声模态。我们借鉴能力拆分，不把已知缺失mask的确定性R0回退等同于所有故障下的鲁棒性，也不直接替换D23已冻结评价条件或门槛。该基准不是RGB–DSM新融合算法。

核对范围：作者摘要、基准定义及Workshop录用说明；未运行其基准。

来源：[作者原文](https://arxiv.org/html/2503.18445v1)；[录用说明](https://arxiv.org/abs/2503.18445)。

## 如何改变下一实验，而不是堆六个模块

**第一优先级候选：比较配对任务收益约束与单纯CE，并检验它是否受冻结表示限制。**这是基于当前损失有益纠错现象及SimMLM思想的推断，尚未实现/验证。先完成既定D23剩余有限对照，再按结果定稿；不修改正在运行的D23，也不重新训练失败TSF来挽救原门槛。

候选采用一个2×2机制对照：

| 表示更新范围 | 标准任务监督 | 配对任务收益约束 |
|---|---|---|
| 专家冻结，只训练相同融合/输出模块 | 冻结CE对照 | 冻结＋配对损失 |
| 预先固定的解码/适配部分可训练 | 同预算可训练CE强对照 | 同更新范围＋配对损失 |

所有组使用相同输入、模型模块、初始化、退化/缺失增强、样本流、有效batch、训练步数、选模和seed；更新范围是有意研究的因子，明确报告可训练参数及计算量，不能声称冻结/解冻计算成本相同。现有部分解冻强基线与M0_safe保留，不能只胜过R0就宣布成功。

具体候选目标：同图全模态/DSM缺失的两视图均有分割监督。先用公开的clean配对MoFe作为可解释基线；若研究区域选择，仅在训练集用固定参考模型的任务误差或训练标签标定有益/有害区域，标签与退化真值不进入推理。质量条件和区域选择相对原MoFe的增量须单独消融，不能与新语义原型、新频率和新骨干同时加入。

此2×2首先回答“改变任务约束是否保留rescue，表示更新是否必要”。收益约束仍可能无效、放大标签噪声或鼓励忽略DSM；须同时报告mIoU、harm/rescue、逐类和逐tile，不能只看训练损失。

**条件优先级：**

- 若D23的TS及shuffleS支持语义对应有增量，再考虑SGMA式类别原型与普通语义特征的同容量对照；原型鲁棒性分数还须对任务收益做校准。
- 若TF/TSF/shuffleF缺乏独立频率增量，撤回当前频率实现的贡献承诺；不为保留第4章强行加入子带。若保留频率，先精读RGSNet并提出DSM特定、可证伪的差异。
- 若转向“缺失时可用分支学习辅助知识”，STARS可作思想对照。该目标会改变固定R0回退的科学问题，须显式另立协议，不能混入D23。
- 区域校准/蒸馏和自适应采样为条件方案。不能把PNDC、SGMA、STARS各拆一个模块拼接后当作已建立创新。

## 去留及尚未解决的问题

新方案必须在看结果前冻结数值门槛、预算和停止条件；本记录不事后更改D23阈值，不批准无限搜索。先验证一个高信息量假设，阶段通过后再安排多种子、未见退化及独立来源；开发Val2正结果不等于确认性论文结果。若收益只来自普通增强/通用解冻，机制不成立；若限制harm必然持续牺牲rescue，换解法或缩小问题。

仍未解决：D23剩余六组原件尚未回读；新损失与可训练范围、增强分布、预算和门槛未冻结；SGMA可执行代码尚未核到；RGSNet全文未取得；STARS划分/通道不匹配；所有借鉴在当前任务均未验证。文献支持研究设计，不替代我们的实验证据。

## 2026-10-01 22:37 后续证据与多角度计划

以上阶段判断及“剩余六组待回读”是20:32历史状态，现由[八组完整结果](../experiments/D23_EIGHT_ARM_RESULTS_20261001.md)取代：全部完成回读，当前S/F没有达到独立增量。用户随后要求今晚多组、参考不同角度；[D24夜间15组](../protocols/D24_OVERNIGHT_MULTIPERSPECTIVE_20261001.md)已定稿，但代码未完成、未启动。

不再以“先证明D23 S有增量”作为类别原型探索的绝对前置：类别槽与通用同容量槽检验不同于旧S拼接的新假设，且是此次用户授权的多角度规划。B借鉴类别原型和类别平衡，不声称复现SGMA模态采样；C借鉴知识迁移与区域校准，不声称复现STARS/PNDC全方法；A使用固定R0 clean参照，与原SimMLM MoFe明确不同。各角度独立对照，不把四篇拆成一套不可解释组合。

旧四组协议的未定项已在新计划具体化；实现、梯度/行为验证及启动仍未完成。SGMA完整代码、RGSNet全文与频率独立新意、STARS划分/通道一致性及独立泛化仍未解决。本文引用的原思想不因开发方案成立就自动成为我们的贡献。
