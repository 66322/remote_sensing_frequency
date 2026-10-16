# D27 文献到实验：安全融合、专家路由与局部贡献（2026-10-02）

本轮为定向检索，不是穷尽系统综述。检索词包含用户四个完整题名、2025/2026 missing modality / robust multimodal segmentation / mixture of experts；优先作者全文、会议开放论文和出版商。以下为重写版建议，不是已有创新或论文正式test结果。

|来源与核验程度|实际可借鉴点|映射与边界|
|---|---|---|
|[BiXFormer作者全文](https://arxiv.org/html/2506.03675v1)、[作者2026出版记录](https://www.cvlab.jp/en/pubs/2026.html)，2025预印本/2026 TMM，10.1109/TMM.2026.3703333|独立模态预测、联合与互补匹配，保留各模态能解决的对象|检查DSM独有正确区域的保留；原方法是mask/query匹配，不能把像素gate称为复现|
|[WAMNet出版商](https://www.sciencedirect.com/science/article/pii/S0925231226010623)，Neurocomputing685:133665，2026，10.1016/j.neucom.2026.133665；可读摘要/介绍，未核对完整实现|非对称频率表征与跨模态交互|启发条件频率专家。不能先验断言DSM高频全是噪声，或把完整输入精度当缺失鲁棒性证据|
|GLFRNet，用户指定2026多模态语义分割题名|全局/局部与频率重建是待核查线索|搜索发现多个同名网络。二手索引给出10.1109/TGRS.2026.3686905，但本轮DOI/IEEE原文未成功读取；不据此引用其模块细节、分数或声称复现。需获得原文再定具体实现|
|[STARS全文](https://arxiv.org/html/2601.17342v1)、[出版商](https://www.sciencedirect.com/science/article/pii/S1569843226002943)，IJAEOG151:105378，2026，10.1016/j.jag.2026.105378|共享/特有表征、双向翻译、stop-gradient对齐、类别平衡采样|解释缺失补偿与保持模态特有线索；本轮单模态回退等值不等于该补偿能力。先保留为独立后续问题|
|[MultiMoE](https://ieeexplore.ieee.org/document/11557397/)，TGRS2026，10.1109/TGRS.2026.3702194|冻结基础编码器、轻量专家适配、动态分配|启发固定骨干比较路由；它使用DINOv3，不直接迁移其分数或同时更换我们的骨干|
|[SimMLM](https://openaccess.thecvf.com/content/ICCV2025/html/Li_SimMLM_A_Simple_Framework_for_Multi-modal_Learning_with_Missing_Modality_ICCV_2025_paper.html)，ICCV2025|动态模态专家与More-vs-Fewer训练约束|本轮保护/恢复目标须有CE对照；D25具体Pair已失败，不直接再跑同配方。CE排序不能当逐像素或mIoU无退化定理|

跨领域联系：安全融合可借鉴选择性预测/拒绝机制，MoE用于条件选择，局部融合对应空间异质性。这些只是可检验的机制关系；不把“加MoE”“加风险损失”独立命名为新贡献。

证据驱动顺序：先确认融合总体有用且伤害可定位；再比较安全目标与普通CE；再区分静态、图像级、局部、类别条件路由。频率模块与缺失知识翻译分别作为条件后续，不一次堆入主实验。
