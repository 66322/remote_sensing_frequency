# Post-A/B后续规划文献核对（2026-10-04）

用途：为[候选池](../protocols/POST_AB_FOLLOWUP_PLAN_20261004.md)提出可证伪假设；不把论文报告的成绩移植为本项目实验证据。以下均采用作者原文/正式论文页面。检索时间2026-10-04；预印本按具体版本引用，不据第三方页面猜会议。

| 原始论文 | 与本项目相关的内容 | 规划对应与边界 |
|---|---|---|
| [STARS: Shared-specific Translation and Alignment for missing-modality Remote Sensing Semantic Segmentation](https://arxiv.org/abs/2601.17342)，Wang等，2026预印本 | 双向翻译、stop-gradient非对称对齐与像素语义采样 | A2的64/64通道划分不能等同整套STARS。A2失败不证明论文方案失败；也没有依据继续扫A权重。优先检查表示入口。 |
| [SGMA: Semantic-Guided Modality-Aware Segmentation for Remote Sensing with Incomplete Multimodal Data](https://arxiv.org/abs/2603.02505)，Wen等，2026预印本 | 多尺度类别原型、模态鲁棒性估计与训练采样 | 启发N4将固定配额、loss加权与动态分配分开。D24单尺度原型失败不等同SGMA全方案失败；N3的局部区域不是复现SGMA。 |
| [EQUISeg: Robust Multimodal Semantic Segmentation with Balanced Modality Contributions](https://arxiv.org/html/2509.24505v1)，Tan等，2025预印本v1 | 分阶段跨模态交互、随机教师学生分组与原型指导 | 启发N1检验交互位置。原文四模态场景不能直接推成RGB–DSM双向成立；平衡不是硬性相同融合权重。 |
| [DFormerv2: Geometry Self-Attention for RGBD Semantic Segmentation](https://openaccess.thecvf.com/content/CVPR2025/papers/Yin_DFormerv2_Geometry_Self-Attention_for_RGBD_Semantic_Segmentation_CVPR_2025_paper.pdf)，Yin等，CVPR2025 | 用深度与空间距离构成几何先验影响注意力 | 启发N2的前向关系传播。俯视DSM不等同透视深度；本项目建议用归一化相对高度，不凭空假设相机内参/米制nDSM。双向扩展是新建议，不是该论文结论。 |
| [Coverage ≠ Exposure: Auditable Control of Same-Support Tail Failures under Multimodal Missingness](https://proceedings.mlr.press/v306/hong26b.html)，Hong等，ICML2026/PMLR306 | 区分输入支持覆盖与参数有效更新，关注相同支持下的尾部可靠性 | 启发N4先看更新记录，再比较采样和加权；不能用D28共同/独立退化结论代替训练暴露检验。N4不是其控制器复现。 |
| [Benchmarking Multi-modal Semantic Segmentation under Sensor Failures: Missing and Noisy Modality Robustness](https://openaccess.thecvf.com/content/CVPR2025W/TMM-OpenWorld/html/Liao_Benchmarking_Multi-modal_Semantic_Segmentation_under_Sensor_Failures_Missing_and_Noisy_CVPRW_2025_paper.html)，Liao等，CVPR Workshops2025 | 区分缺失与噪声情况下的多模态鲁棒性 | 支持E1把缺失、退化、方向分开报告，不能据总平均声称各种失效都解决。该文为workshop，不能误标主会。 |

## 由文献到实验的推论

共同启发是：改变交互发生的位置、关系表示或训练分配，可能比在相同冻结末端特征上再加一个损失更值得检验。这是本项目根据代码与结果作出的推论，文献没有证明我们的瓶颈所在。

至少保留三种反证：等参数普通融合追平；真实空间关系不如打乱关系；动态策略不超过固定平衡。这些结果都应关闭复杂机制，不改门槛挽救。

N5内容相关缺失是问题设定扩展建议，需锁定输入生成规则与同面积控制；不能自动称为自然故障或真实MNAR数据。N6教师来源检验是C成功后的归因，不是C失败后的调参分支。

本轮没有把已有方法简单改名作为创新，也没有认定这些论文在本项目已被复现。后续若做公开方法基准，必须另核对官方代码版本、训练预算、预训练数据和缺失设定；当前候选池中的受控变体应写“受启发的适配”。
