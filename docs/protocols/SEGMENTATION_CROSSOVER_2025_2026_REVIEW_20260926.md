# 2025–2026 分割与交叉方向：候选筛选及次日验证议程

记录日期：2026-09-26。性质：**重写版建议，尚未实现或实验验证**。
用户要求扩大近期论文调研范围，并在本轮结果就绪后一起验证。
本文件只形成候选与条件化计划，不修改 D16/D17 配置，不向服务器追加任务。

## 研究判断

围绕一个重要问题建立一个核心方法贡献，必要时配套一至两个紧密相关机制。
不同方向是备选问题，不是准备装进同一网络的模块清单。

现有证据支持继续研究有条件的 RGB–DSM 互补：D15 的 RGB down4 条件下，
R05 相对较强 RGB 对照的收益在两个 seed、两个 Val tile 上均为正。
但这不能证明对所有输入质量都有效，更不能证明因果识别。
D13 的风险约束同时压低 harm 和 rescue；仅降低对 DSM 的依赖不是目标。
详见 [D15 原始归档审计及结果](../experiments/D15_RESULTS_20260926.md)、
[D13 结果](../experiments/D13_RESULTS_20260925.md)。

优先顺序：当前干预机制结果 → 几何/边界的独立机会 → 点监督实例分割备选。
计算效率、跨域、开放词汇和遮挡补全保留为条件化路线。
不因当前某个候选失败就判定整个多模态方向无意义，也不为延续方向反复调整门槛。
原 [D16/D17 组合计划](D16_D17_RESEARCH_PORTFOLIO_20260926.md) 中的预训练表示/适配器
对照仍保留：若机制收益受骨干表示限制，可先做该有界对照，再决定是否换任务。
近期 RobustSeg 提供另一种表示学习参考，但已有静态教师蒸馏失败记录不能忽略。

## 来源、年份与阅读深度

这是面向本项目的定向筛选，不是穷尽性的系统综述。
新增核对八篇 2025–2026 论文，并与先前已核对的 ISFuse 对照。
检索与主张依据为 CVF 论文页面/原文、arXiv 作者版本和作者仓库；
首选检索工具本地不可用，使用网页检索作为替代。
除 ISFuse 外，本次主要完成元数据、摘要/原文首页及部分仓库核对，
不声称已经逐篇精读全文、审计全部实现或复现结果。
部分 CVF 页面后续重访返回403；可读的作者版本作为补充，不能据此扩展未读细节。

| 文献及可核对来源 | 年份/状态与本次阅读 | 可借鉴问题与迁移边界 |
|---|---|---|
| [DFormerv2: Geometry Self-Attention for RGBD Semantic Segmentation](https://openaccess.thecvf.com/content/CVPR2025/papers/Yin_DFormerv2_Geometry_Self-Attention_for_RGBD_Semantic_Segmentation_CVPR_2025_paper.pdf)；[作者代码](https://github.com/VCIP-RGBD/DFormer) | CVPR 2025；原文首页/摘要 | 深度与空间关系形成几何注意力先验。启发我们研究几何关系如何帮助分割；DSM 是地表高度，不等同于相机深度，不能直接套用投影几何。 |
| [Topology-Preserving Image Segmentation with Spatial-Aware Persistent Feature Matching](https://openaccess.thecvf.com/content/ICCV2025W/BIC/html/Wen_Topology-Preserving_Image_Segmentation_with_Spatial-Aware_Persistent_Feature_Matching_ICCVW_2025_paper.html) | ICCV 2025 **BIC Workshop**；官方摘要 | 用空间位置辅助持久拓扑特征匹配，原应用是管状生物医学结构。可借鉴连接/断裂的任务定义；不能给所有遥感类别施加连通约束。 |
| [ReSAM: Refine, Requery, and Reinforce: Self-Prompting Point-Supervised Segmentation for Remote Sensing Images](https://arxiv.org/abs/2511.21606)；[作者仓库](https://github.com/MNaseerSubhani/ReSAM) | 2025 预印本，2026 修订；作者 README 标注 CVPR 2026 Main Track 接收，本次未单独核对到 CVF 条目。摘要/README | 稀疏点生成伪掩码，再由自构建框提示细化并进行语义对齐。适合讨论标注成本与提示可靠性，不能将已有全监督权重用于伪装低标注训练。 |
| [SCORE: Scene Context Matters in Open-Vocabulary Remote Sensing Instance Segmentation](https://www.openaccess.thecvf.com/content/ICCV2025/papers/Huang_SCORE_Scene_Context_Matters_in_Open-Vocabulary_Remote_Sensing_Instance_Segmentation_ICCV_2025_paper.pdf)；[作者版本](https://arxiv.org/abs/2507.12857) | ICCV 2025；原文首页/摘要 | 区域和场景上下文辅助开放词汇实例识别。启发分割与语言/上下文结合；需真实实例标注和独立的新旧类别协议。 |
| [Segment Anything, Even Occluded](https://openaccess.thecvf.com/content/CVPR2025/papers/Tai_Segment_Anything_Even_Occluded_CVPR_2025_paper.pdf)；[作者版本](https://arxiv.org/abs/2503.06261) | CVPR 2025；官方来源及作者摘要 | SAMEO 将 SAM 作为可适配前端检测器的遮挡完整掩码解码器，使用合成 Amodal-LVIS。启发分割与补全；当前类别标签不包含真实不可见部分。 |
| [Foveated Instance Segmentation](https://openaccess.thecvf.com/content/CVPR2025/html/Zeng_Foveated_Instance_Segmentation_CVPR_2025_paper.html) | CVPR 2025；官方摘要 | 以注视信息集中计算到感兴趣实例，原场景是 AR/VR。可借鉴按需分配计算；本项目没有眼动数据，区域选择器属于新设计。 |
| [Towards Robust Multi-Modal Semantic Segmentation with Teacher-Student Framework and Hybrid Prototype Distillation](https://openaccess.thecvf.com/content/CVPR2026/html/Tan_Towards_Robust_Multi-Modal_Semantic_Segmentation_with_Teacher-Student_Framework_and_Hybrid_CVPR_2026_paper.html) | CVPR 2026；官方摘要 | RobustSeg 结合反馈式教师学生学习与跨模态/类内原型信息，面向不完整模态。已有普通教师蒸馏负证据，只有提出不同、可检验机制才值得再试。 |
| [Hyperbolic Prototype Learning with Uncertainty-Aware Consistency for Continual Test-Time Segmentation](https://openaccess.thecvf.com/content/CVPR2026/html/Gole_Hyperbolic_Prototype_Learning_with_Uncertainty-Aware_Consistency_for_Continual_Test-Time_Segmentation_CVPR_2026_paper.html) | CVPR 2026；官方摘要 | HyperProtoSeg 区分稳定核心与不确定区域，在持续域变化中进行原型适应。原评估是驾驶场景；在同两张遥感 Val 图上添加模糊不等于跨地域泛化。 |

先前的 [ISFuse 原文与代码核对](ISFUSE_TRANSFER_REVIEW_20260926.md) 比上述筛选更深入，
包括必要性损失符号和门控熵项的解释问题。这里不把所有论文归结为同一种“稳定特征”，
也不把搬用已有注意力、SAM 或原型损失本身算作本项目创新。

## 候选问题与最小可证伪实验

### P1：分割 × 干预学习，保留有益互补而非单纯保持预测不变

- **重要问题：** RGB 与 DSM 质量变化时，哪些跨模态关系有利于正确分割？
- **现有依据：** D15 有条件互补；D16 正在比较一般一致性、任务条件一致性与打乱对照。
- **重写版建议：** 结构化干预结合任务效用约束；只有对分割正确性有益的关系才应保留。
- **最小检验：** 先分析 A0/A1/A2/A3 和 A4/A5。若没有超越一般增强/一致性的证据，
  暂不靠增加 CFI 挽救同一假设。若信号成立，再采用既有 ISFuse 六配置矩阵，
  拆开结构、干预和任务约束。
  当前失败不能反证所有干预结构无效；另一结构若要立项，必须提出区别于当前正则化的新假设。
- **继续条件：** 按已冻结门槛取得方法收益，且 rescue 没有随 harm 一起塌缩，
  收益不能由匹配的 RGB 对照解释。否则记录失败，停止当前机制扩展。

### P2：分割 × 几何关系/边界恢复，解决轮廓错位与粘连

- **重要问题：** 颜色纹理不清时，能否利用高度结构帮助区分物体边界？
- **最小检验先于训练：** 对完成的基线和 B1/B2 做 FullGT 边界带/内部区域的误差拆分，
  按建筑、树木等类别和 tile 查看，确认几何线索与失败模式是否相关。
  若归档只有混淆矩阵，无法重建边界位置，需另行生成验证集预测掩码并绑定权重。
- **后续三配置：** 相同分割基线；对齐几何关系约束；打乱空间对应关系的同预算约束。
  不重复包装 D17 已有的 DSM 梯度辅助监督；必须先指出新约束与其差别。
- **指标：** 原 NoBoundary fg5 主指标保持可比；FullGT 边界 F-score/Boundary IoU 为新增诊断，
  容差与尺度在运行前固定。NoBoundary 排除边界，不能单独支持边界改善结论。
- **停止条件：** 几何对齐不优于打乱、收益只是内部分类改善，或 clean/其它类别明显受损。
  连通分量仅作语义掩码诊断，不冒充真实实例；不透水面标签不等于道路拓扑标注。

### P3：点监督/交互分割 × 提示可靠性，降低密集标注成本

- **重要问题：** 只有少量点提示时，如何防止错误伪掩码在训练中传播？
- **优先级：** 如果需要开辟一个不同于当前鲁棒融合的问题，这是优先备选。
- **明天可验证：** 核对 ReSAM 数据/权重许可、真实实例标注、预训练来源和环境。
  作者环境要求与当前 Python3.9 环境不同，应独立环境复现，不升级正在训练的环境。
- **最小实验：** 同一公开预训练起点、同样点标注预算，比较原始 SAM 提示、
  官方点监督基线、稳定性筛选伪掩码、随机筛选同等数量伪掩码。
  筛选策略不能访问隐藏的训练全掩码，完整验证标注只用于最终指标。
- **迁移限制：** 已使用 Train16 全标签训练的 R01/R05 不可充当低标注公平起点。
  若使用外部 RGB 实例数据而没有 DSM，则这是独立路线，不能声称验证 RGB–DSM 效果。
- **继续条件：** 超越同标注预算、同保留样本数量的对照，并且改善跨图像成立；
  数据许可、标签或基础复现未通过时，不排正式训练。

### P4：分割 × 按需计算，回答何时值得调用 DSM 分支

- **重要问题：** 能否在保持精度的同时，减少不必要的第二模态计算？
- **借鉴边界：** Foveated Instance Segmentation 的计算分配思想可参考；
  自动选择遥感区域与眼动引导是不同问题。
- **最小检验：** 先用验证预测估计区域互补机会，再实现提前跳过分支的简化原型，
  比较全量双模态、置信度选择、随机选择和候选选择器，在相同计算预算下比较。
  基于真值的 oracle 只作上限诊断，不能用于部署或选实际区域。
- **继续条件：** 实测端到端延迟/显存与精度形成收益，包含选择、裁剪、数据搬运和拼接开销。
  两个大分支都算完再乘门控不能宣称省计算。测时需要 GPU 独占，不能受并发训练干扰。

### P5：分割 × 跨地域/测试时适应，减少新场景中的伪标签累积错误

- **重要问题：** 更换地域/传感器后，如何适应而不把错误预测不断强化？
- **最小检验：** 先获得独立地域/传感器数据并核对标签映射，再比较冻结模型、
  简单适应、候选原型/一致性适应。提前固定样本顺序、复位规则和更新预算。
- **约束：** 当前反复使用的 Val2 只能做探索。同图像合成退化不构成独立地域证据。
  Test6 release gate 未开放，即使无监督适应也不得加载 Test6。
- **停止条件：** 没有独立数据，或同预算简单适应已经解释全部改善。不要同时加入原型、
  双曲空间、教师反馈多个机制，导致无法归因。

### P6：实例分割 × 开放词汇，识别训练时没有标注的新类别

- **重要问题：** 新类别难以补齐实例标注时，能否利用语言与场景上下文定位并分割？
- **参考：** SCORE，区别于给固定类别加文字提示的封闭集分类。
- **明天可验证：** 检查公开实例数据、base/novel split、文本词表和评价脚本是否可用。
  类别语义标签的连通域不能自动成为可靠实例 ID。
- **最小后续对照：** 原开放词汇实例基线；上下文机制；打乱文本/上下文对照。
  先冻结类别与预训练暴露协议，再决定是否有必要引入 DSM。
- **停止条件：** 新类别设定无法成立，或没有实例级真值。此路线数据和代码迁移成本高于 P1/P2。

### P7：遮挡完整分割 × 几何补全，恢复可见与不可见的对象范围

- **重要问题：** 建筑或车辆被遮挡时，能否恢复完整范围而不虚构结构？
- **参考：** SAMEO；与普通可见区域语义分割不同。
- **明天可验证：** 只做完整对象标注和数据来源可行性检查。若只有当前语义标签，
  不安排有“真实遮挡补全”结论的训练。
- **后续对照：** 可见掩码基线、图像补全条件、几何条件，在有 amodal 真值的协议上比较。
  合成遮挡只能证明该合成协议下恢复能力；DSM 也不提供真实被遮挡表面高度。
- **优先级：** 高成本储备；先看有无可信数据，再谈网络。

## 明天如何使用两张 GPU

1. **先完成当前结果审计。** 最后已观测的服务器状态见 handoff；本文件不推测实时状态。
   当前队列没完成就继续，先做文献、数据和已归档结果的 CPU 分析。
2. **决定一条主路线、一条备选。** P1 取决于 A 系列，P2 取决于 B 系列及边界诊断；
   若两者都缺乏信号，先区分是否需要原计划的预训练表示对照；并优先验证 P3 的数据与基础方法
   作为换问题备选，不同时启动七个研究方向。
3. **未来队列先有完整闭环。** 为入选路线准备固定配置、训练→保存→重新加载→评估→汇总；
   先验证正式训练与评估的全部分支，再提交有限任务列表。独立任务失败可继续其它独立任务，
   依赖失败的任务必须跳过并明确报告。现有 D16/D17 队列此次不变。
4. **共享 GPU0/1 的就绪任务队列。** 对未来新方向先完成 seed42 的必要对照，
   只有通过预先约定筛选的候选与相应对照再补 seed17，避免只复验赢家而缺少公平对照。
   两卡均可执行就绪训练或评估，不固定一张卡空等另一张卡完成串行评估。
5. **运行预算在 smoke 后估计。** 当前 A0 初始速度不能直接套给 SAM、新注意力或稀疏推理。
   每个新结构先测稳定训练吞吐、显存和一次评估时长，再计算整批预算，可跨一天继续。
   “明天验证”包括可行性和小规模检验，不意味着所有方向明天都能得出研究结论。

## 论文收敛与立项门槛

每个候选用同一张卡片立项：一个重要问题 → 现有方法的具体不足 → 一个核心假设 →
最近工作差异 → 最小公平对照 → 成功/停止条件 → 独立验证来源。
已有算子迁移、更多损失项、普通消融数量都不自动构成创新。
优先选择既有可测失败模式、又能通过反例推翻假设的路线。

本轮交付是研究计划，不是实验完成记录；不向实验 registry 写入虚构运行ID或结果。
