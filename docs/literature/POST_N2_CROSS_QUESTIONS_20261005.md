# N2后续交叉问题：原始文献核对与迁移边界（2026-10-05）

用途：支持[后续实验规划](../protocols/POST_N2_EVIDENCE_LED_PLAN_20261005.md)，不是系统综述或已完成官方方法复现。检索/核对2026-10-05，使用作者arXiv、CVF、PMLR等原始来源；无外部模型审稿或私有实验数据上传。论文的实验成绩不移植为本项目结果。

| 文献与核对来源 | 实際核对范围/可用观点 | 本项目映射与局限 |
|---|---|---|
| Yin, Cao, Cheng, Hou. DFormerv2: Geometry Self-Attention for RGBD Semantic Segmentation. CVPR2025. [正式PDF](https://openaccess.thecvf.com/content/CVPR2025/papers/Yin_DFormerv2_Geometry_Self-Attention_for_RGBD_Semantic_Segmentation_CVPR_2025_paper.pdf)、[作者原文v1](https://arxiv.org/html/2504.04701v1) | 正式来源检索、作者HTML方法3.1/3.2：深度差与空间距离构成几何先验并影响注意力。正式PDF直接打开曾返回403，方法核对用作者HTML。 | N2当前关系、N3区域归属的启发；不是论文复现。俯视归一化DSM不是透视深度、米制nDSM或相机3D，双向扩展由本项目提出。 |
| Mei, Chen, Yuille, Xie. SPFormer: Enhancing Vision Transformer with Superpixel Representation. [arXiv:2401.02931v1, 2024](https://arxiv.org/html/2401.02931v1) | 作者HTML摘要和3.2：局部pixel-to-superpixel及superpixel-to-pixel交互，内容自适应区域。 | N3需用固定网格和单侧区域作对照；超像素本身已存在，不能当本项目创新。这里只按核对版本引用；OpenReview正式页面有验证挑战，不依据检索摘要/作者主页不同月份断言正式出版日期。 |
| Jia et al. GeminiFusion: Efficient Pixel-wise Multimodal Fusion for Vision Transformer. ICML2024, PMLR235:21753–21767. [正式页面](https://proceedings.mlr.press/v235/jia24b.html) | 正式元数据与摘要：对齐表征上的像素级跨/内模态交互，强调计算效率。 | 提醒区域方法必须超过普通像素融合，不能删除局部强控制；本项目基座不冒称GeminiFusion官方实现。 |
| Liao et al. Benchmarking Multi-modal Semantic Segmentation under Sensor Failures: Missing and Noisy Modality Robustness. CVPR Workshops2025:1576–1586. [正式页面](https://openaccess.thecvf.com/content/CVPR2025W/TMM-OpenWorld/html/Liao_Benchmarking_Multi-modal_Semantic_Segmentation_under_Sensor_Failures_Missing_and_Noisy_CVPRW_2025_paper.html)、[作者v3全文](https://arxiv.org/html/2503.18445v3) | 正式元数据和作者原文§3：分别评价全缺失、随机缺失和噪声，使用DELIVER场景。 | E1/E2分别检验位置内容与标记可靠性；后两点是我们的扩展问题，不说论文已验证它们。DELIVER结果不能直接支持遥感真实故障；缺失率匹配也不保证内容分布匹配。 |
| Hong, Chen, Liu, Cai, Lu. Coverage ≠ Exposure: Auditable Control of Same-Support Tail Failures under Multimodal Missingness. ICML2026, PMLR306:43508–43537. [正式页面](https://proceedings.mlr.press/v306/hong26b.html) | 正式元数据/摘要核对：输入支持覆盖和受门控参数的更新暴露不同，提出TailPressure/H-CES。未进行全公式/官方实现复现。 | N4先验证条件暴露而非凭弱侧分数猜测；N2有own CE与抽样梯度布尔记录，不能认定论文机制在这里已存在，也不能把普通动态抽样叫H-CES复现。 |
| Wen, Liao, Xiao, Wang. SGMA: Semantic-Guided Modality-Aware Segmentation for Remote Sensing with Incomplete Multimodal Data. [arXiv:2603.02505v1, 2026](https://arxiv.org/abs/2603.02505) | 作者摘要/元数据：多尺度类别原型的融合与模态感知采样。按所查预印本版本引用。 | 提供语义条件与训练分配的参考；本项目D24原型或D8类别采样失败不等于SGMA整套失败，但不能换名字重复既有负配方。 |
| Wang et al. STARS: Shared-specific Translation and Alignment for missing-modality Remote Sensing Semantic Segmentation. [arXiv:2601.17342v1, 2026](https://arxiv.org/abs/2601.17342) | 作者摘要/元数据：双向翻译、stop-gradient非对称对齐与像素语义采样。按所查预印本版本引用。 | A/C失败只约束我们的对应实现，不关闭整类问题；当前不因该文重新启动A对齐或C教师KL。 |

## 从论文到问题，而非拼模块

1. **内容相关缺失 × 分布变化**：E1/N5改变的是缺失位置分布，固定面积、形状、训练量；“合成内容相关”不自动等于统计意义MNAR，更不等于自然传感器故障分布。
2. **空间支持 × 双向互补**：E0/N3检验同一对象内与跨边界信息混合。需要区域与固定网格对照，论文出现超像素不能证明当前项目应加超像素。
3. **条件覆盖 × 优化更新**：N4须有参数/条件暴露证据，不能把出现过输入状态、像素计数或非零梯度当成等量有效学习。当前两侧own CE削弱“某侧完全没更新”的简单解释。
4. **物理缺失 × 标记误差**：E2保持物理损伤tensor固定再独立改变availability标记。先诊断工程回退依赖，不自动建立置信网络。
5. **方法增量 × 强基线解释**：C0已解释C主要提升，N1-2已解释普通适应收益；新方案必须超过匹配控制，单次微小正差不升级贡献。

未建议：重跑PCGrad/状态分头（D25已有负结果）、重新类别采样救D8、A/B权重/窗口扫描、换教师救C、追加种子、把任务恢复升主线。若未来做完整公开方法基准，另核官方版本、训练预算、预训练来源与输入设置；本轮仅完成文献支持的实验设计。
