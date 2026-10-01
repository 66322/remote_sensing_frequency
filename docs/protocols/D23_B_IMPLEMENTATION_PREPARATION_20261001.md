# D23-B实现准备记录

日期2026-10-01。A已满足准备门槛；8组gate核心代码与8项本地CPU合成测试已实现/通过，服务器环境复验、真实冻结专家接入、训练/整图评价入口及正式训练均未完成。此文件不是启动GPU队列。

代码：model/rebuild_v1_d23_gate.py；测试：tests/test_d23_gate.py。专家通过现有D21 R0/M0实例注入，不修改历史源码。FrozenExpertPair定位decoder[3]分类层前128通道并检查低分辨率/完整logits精确一致，全部参数冻结，保持eval；暂不共享DINO tokens。8组均18,145可训练参数、276输入、hidden32和相同零初始化末层。E16、S256、F4，缺失位置torch.where取同R0；整图拼接后回退须由未来评价入口再次执行。

TCAP没有默认训练统计：未set_fit_statistics即拒绝；统计必须由12 gate-fit tile计算，不能读取Val2。loss_sums提供CE、正/负BCE的sum与count，combine_loss_sums按有效batch合并，避免改变microbatch时重权重；训练引擎必须预先求有效batch分母，不能把每microbatch独立平均后直接累积。干净/退化两视图权重与原4000步计划保持，标签仅进loss。

本地PyTorch2.7.1+cpu，8项测试使用小型合成输入和ToyExpert：等参数/初始化；信息屏蔽与空间打乱；8gate＋6固定方法缺失精确回退；全batch/分块loss与梯度一致；纠错/伤害监督梯度方向及空集合；128通道hook和gate-only两步优化/专家状态不变；TCAP统计前置/输入拒绝；常量及奇数尺寸频率。此证据不代替服务器PyTorch2.2.2或真实DINO吞吐/精度。

下一顺序：补A完整JSON轻量归档；服务器CPU复验核心；实现单一fit采样/训练与整图评价入口（按需加载，小LRU）；真实专家/GT/availability与样本随机键审计；GPU单卡有界microbatch短测及整图重现；填wall/job、RSS/显存/磁盘保护；再生成正式8组运行命令。不改变原开发/封存边界、不以代理指标选赢家。
