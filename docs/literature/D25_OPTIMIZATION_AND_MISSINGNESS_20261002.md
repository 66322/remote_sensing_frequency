# D25文献映射：完整/缺失优化取舍

检索日期2026-10-02。定向检索2024—2026相关原论文并补充基础方法，不是系统综述；只把可核对的方法用于假设设计，不移植论文分数到本数据。下列为简要方法映射，完整贡献边界须在形成候选后进一步对照。

| 原始来源及状态 | 本次读到的方法要点 | 对D24/D25的意义与限制 |
|---|---|---|
| [DGL，ICCV 2025，Wei等](https://arxiv.org/html/2507.10213v1)，[官方代码](https://github.com/shicaiwei123/ICCV2025-GDL) | 将编码器与融合模块的梯度路径分开，讨论单模态欠优化；包含RGB-D分割实验 | 支持测量优化干扰。D25保留完整任务梯度、只投影冲突缺失梯度，是受启发的诊断性改写，不是DGL复现，也不以改名声称新算法 |
| [ConD，2026-07预印本](https://arxiv.org/html/2607.20326v1) | 冻结原模型、复制可训练编码器，以零初始化特征注入学习缺失条件；NYUv2/SUN RGB-D | 支持保留完整能力并适配缺失的思路。推理实际增加复制编码器开销；尚不能据此保证遥感有效。D25先用轻量分头和梯度对照，完整ConD适配列后续强对照，未复现 |
| [RTFDNet，2026-03预印本](https://arxiv.org/html/2603.09149v1) | RGB-T独立与融合分支，含stop-gradient的跨模态/区域约束，单模态可独立推理 | 支持显式保留单模态分支；本轮先检验分头，暂不叠KD。其热红外场景与DSM不同，不能借用精度或声称复现 |
| [SGMA，TGRS 2026](https://ieeexplore.ieee.org/document/11517493)，[方法全文](https://arxiv.org/html/2603.02505v1)，[仓库](https://github.com/wenlk3/SGMA) | 多尺度类别语义与模态感知采样联合设计 | D24单尺度EMA bank+类别平衡CE并非完整SGMA，因此负结果不否定该论文。本次仓库仍仅README、标注代码将发布，不能称官方代码已复现；本轮不再复制原型模块 |
| [SimMLM，ICCV 2025](https://openaccess.thecvf.com/content/ICCV2025/papers/Li_SimMLM_A_Simple_Framework_for_Multi-modal_Learning_with_Missing_Modality_ICCV_2025_paper.pdf)，[全文](https://arxiv.org/html/2507.19264v1) | 专家混合与More-vs-Fewer任务损失排序 | D24是固定R0参照的改写，且Pair开关未生效；不得用它否定MoFe。P1修复原改写，只比较正确信号，仍不是原文复现 |
| [传感器故障基准，CVPR Workshops 2025](https://openaccess.thecvf.com/content/CVPR2025W/TMM-OpenWorld/html/Liao_Benchmarking_Multi-modal_Semantic_Segmentation_under_Sensor_Failures_Missing_and_Noisy_CVPRW_2025_paper.html) | 区分整幅缺失、随机缺失、噪声及不同失败概率 | D25分开报告完整/退化/全缺失/局部缺失，新增组合压力条件；不把workshop写成CVPR主会，不把等权综合当部署期望 |
| [PCGrad，NeurIPS 2020，Yu等](https://proceedings.neurips.cc/paper_files/paper/2020/hash/3fe78a8acf5fda99de95303940a2420c-Abstract.html) | 对冲突任务梯度作投影 | 是投影思路的直接已有来源。D25单向保护只是机制对照；必须与不投影及同幅度缩放比较，成功也不自动构成方法创新 |

本轮建议只检验两个新解释：共享decoder的状态耦合、共享表征的完整/缺失梯度冲突。Pair另作技术纠错。频率/语义仍是允许保留或替换的工具，不是论文强制组件；待稳定强基线下有针对性证据，再决定是否用几何/频率信息处理空间错位或边界。这里没有将任务驱动恢复升为主线。
