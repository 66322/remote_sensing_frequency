# Phase 1.5 文献思想到可检验问题（2026-10-12）
这是定向原始来源核对，不是穷尽综述或全代码复现。下表中的实验映射都是重写版建议，文献结果不等于本项目验证。优先完成零训练诊断，再决定选用哪一项。

|原始来源|核对到的思想|本项目具体吸收|边界/反对照|
|---|---|---|---|
|[STARS，arXiv:2601.17342v1](https://arxiv.org/html/2601.17342v1)|遥感缺失模态中的共享/特有表征、双向翻译与stop-gradient、类别采样对齐|A/C先判断真实DSM对应内容和类别差异；若后来训练知识迁移，保留特有信息并设普通任务训练对照|本轮核对预印本方法，不主张其所有机制已在当前局部缺失成立；stop-gradient不是万能防塌缩保证|
|[TokenFusion，CVPR 2022](https://openaccess.thecvf.com/content/CVPR2022/html/Wang_Multimodal_Token_Fusion_for_Vision_Transformers_CVPR_2022_paper.html)|以跨模态信息替换不充分token，并保留位置对齐|用A与D检验真实空间信息是否优于置换、何处值得替换|不能把当前M000 replacement失败外推到所有token替换，也不能换名称重复旧配方|
|[Predictive Dynamic Fusion，ICML 2024](https://proceedings.mlr.press/v235/cao24c.html)|融合中的单模态与联合置信信息以及相对校准|D先检验可观测统计与专家正确性是否相关、跨tile是否一致，再考虑预测级router|熵不等于正确率；理论界不直接保证Potsdam每像素安全。此处核对正式摘要/书目信息，未复现证明与源码|
|[SimMLM，ICCV 2025](https://openaccess.thecvf.com/content/ICCV2025/html/Li_SimMLM_A_Simple_Framework_for_Multi-modal_Learning_with_Missing_Modality_ICCV_2025_paper.html)|动态模态专家与More-vs-Fewer排名目标|下一训练必须保留普通CE/静态专家对照，分解专家是否有用和选择是否有效|相关旧D25/D27配方已有负结果，不直接再训练同样排名/gate；论文目标不代表逐像素mIoU不下降定理|
|[ControlNet，arXiv:2302.05543](https://arxiv.org/abs/2302.05543)|冻结预训练主体、通过零初始化连接加入可训练条件分支|仅作为未来冻结anchor＋残差适应的工程参考|原任务为生成；zero-init仅保证初始输出，训练后clean恒等需显式旁路，混训不是数学保证|
|[Benchmarking Multi-modal Semantic Segmentation under Sensor Failures，2025](https://arxiv.org/abs/2503.18445)|区分整体缺失、随机缺失与噪声模态，分别评价鲁棒性|本轮专注局部RGB缺失；后续方法必须补双向质量/缺失评价，避免单一synthetic zero推论|不把两tile多mask当跨域确认，不为本轮盲目增加新数据/训练|

这些文献支持提出可检验对照，不支持宣称“router能捕获oracle的20–40%”、本项目训练seed方差0.2–0.5pp、某路径必然可发表或具备独立创新。生成式恢复、VAE或结构中间域暂不增加实验；待现expert的共同错误与可用信息分析后，才判断是否需要。
