# D25建议计划：完整模态收益与缺失能力的优化取舍

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: plan
- Origin Date: 2026-10-02
- Verification Status: IMPLEMENTED_LOCAL_CPU_PASS；用户已授权，服务器启动观测待回传
- Version Label: D25_execution_v1
- 决定来源：用户进一步明确“按上述实验规划进行具体实验”，八组执行已授权；不等于贡献已成立。固定执行见[D25执行说明](D25_EXECUTION_20261002.md)。

## 问题、证据与两个假设

主问题不变：光学输入可用时保留DSM有益融合，控制质量变化的负迁移，并在DSM全幅/局部缺失时保留分割能力。不是重新转向第2章恢复，也不要求频率/语义都留在最终方法。

[D24复核](../experiments/D24_REVIEW_AND_PAIR_CORRECTION_20261002.md)中，Q-only的D1 clean87.0707、全缺失82.4742；QD的A2 clean86.9035、全缺失86.1431。全缺失+3.6689而clean−0.1672；已有可运行回退仍可能精度弱。H1：两个输入状态共用decoder限制了兼顾能力，显式分头能缓解。H2：在共享编码器上完整/缺失监督梯度冲突，抑制冲突比只减小梯度幅度有效。二者都是待验证解释，不由现有指标直接推出。

[文献映射](../literature/D25_OPTIMIZATION_AND_MISSINGNESS_20261002.md)包括DGL/SimMLM（ICCV2025）、SGMA（TGRS2026）、ConD/RTFDNet（2026预印本）和传感器故障基准（CVPRW2025）。梯度投影本身已有PCGrad来源；分头、投影或其组合不预先声称新颖。Pair作为D24技术无效消融的修正，不作为第三个新主线。

## 八组及匹配关系

| ID | 处理 | 主要回答 |
|---|---|---|
| P0 | last4、共享decoder、CE、QD | 同轮新鲜强基线，复用A2配置但不复用其结果代替控制 |
| P1 | P0＋修正开关后的原anchored Pair，权重0.1 | 正确施加原目标是否有增量；只修正，不扫lambda |
| P2 | 完整/缺失各一个decoder，CE、QD | H1；与P0和P5比较 |
| P3 | P2＋单向冲突梯度投影 | H2；与P2、P7及P0比较 |
| P4 | P0＋相同投影 | 无分头时投影是否有效；与P0比较 |
| P5 | 两个都参与完整/缺失路径的decoder，logit等权平均 | P2参数数量/额外解码计算对照；两个头均参与反传 |
| P6 | 从同一M0复制光学编码器/decoder，仅RGB、CE、Q | 配对初始化的独立光学强基线；避免把R0初始化C0当严格同初始化控制 |
| P7 | P2＋与投影后相同模长的缺失梯度缩放，方向不变 | 区分冲突方向修正和简单减弱缺失梯度 |

P0/P2/P4/P3组成分头×投影的2×2；P5排查参数计数，P7否证方向机制，P6检查强光学参照，P1修正Pair。P5两头都从同一M0 decoder复制；对称初始化可能保持相关，因此它仅是参数数量对照，不足以证明全部函数容量等价。P2如果仅赢P0却不赢P5，不宣称状态分头有独立机制收益。

## 可实现定义

所有融合组仍使用D24的DINO last4、RGB投影、DSM detail和可用性mask。P2/P3/P7分别用D_f解码feature+masked DSM，用D_o解码feature；像素输出where(available,full,optical)，保留局部缺失精确回自身光学。D_f/D_o同源复制M0 decoder；不接训练标签、退化类型真值或oracle到推理。P5在两种特征输入上均计算两个decoder并平均logits，再使用同一availability规则。P6从同一M0删去DSM支路；它是独立训练对照，不与融合模型的own_optical混写。

训练监督沿D24：L=0.5 CE(clean)+0.5 CE(QD)。将L严格拆为L_present和L_missing：clean全属present；aug像素按known availability分区求和，**均除以原aug全部有效像素数**，不能改成两区各自均值而暗中重加权。其和须数值等于原CE。P1另外加原clean固定R0参照hinge，不用动态阈值或新教师。

共享参数上的g_p=grad(L_present)、g_m=grad(L_missing)，使用同批同前向，FP32梯度。全共享向量拼接后计算d=<g_p,g_m>；d<0且||g_p||²>1e-12时，g_m'=g_m−d/(||g_p||²+1e-12)·g_p；否则保持g_m。更新梯度g_p+g_m'。单任务专属参数不投影，沿各自loss更新；同一batch只有一次optimizer.step，不是梯度累积。P7以||g_m'||/max(||g_m||,eps)乘原g_m；无冲突时系数1，零梯度保持0。P7与P3同架构同样计算原梯度，仅改变方向处理。

P3共享参数是last4和RGB投影；P4还包含共享decoder。P2/P7各decoder沿自己的像素监督；DSM分支仅沿present监督。按真实参数梯度依赖确定shared集合并记录，不能手写错误范围。投影前后使用一致的既有gradient clipping/AdamW设置；若D24未用clip则全组不新增。点积性质不是AdamW后真实损失或mIoU不下降的保证。

在正常训练每100步记录共享梯度cos、两任务norm、冲突比例、投影后norm、present/missing有效像素、两decoder各自非零梯度；不另开资源审计。两头/投影的实际计算与可训练参数计数必须记入配置，新增模块不得只检查总loss能反传。

## 数据、预算与选模

全部从D21 M0同一权重初始化（SHA23b2939ea50867c96c0a17626fd4a85a27100ebd8296b2fc96440ed8bc3d34de），fresh optimizer；不从D1/A2选中checkpoint继续以免上游预算和选模混淆。P1固定R0教师沿D24 SHA。D24原件仅作历史参照，P0为同轮匹配基线。

沿用D24固定Potsdam fit12/Val2、seed42、512crop、对齐scale0.5–2/flips；相同keyed裁剪和Q/D抽样。每组4000更新，8组共32000；物理batch16、不累积、两view、BF16训练/FP32评价；AdamW head2e-4、last4 2e-5、WD0.01，100步warmup、线性衰减到4000。checkpoint每500步；2000/4000 clean Val2 NoBoundary fg5选模，平局选早期。P6的Q图像与其他组同源，D不改变它的输入。Test6禁读；历史held4不包装成独立holdout。

复用14条件、native512/stride256评价，保存Full与NoBoundary的6×6 int64矩阵、TP/FP/FN/support、逐类/逐tile、harm/rescue、available/missing和自身光学参照。分别报告available综合、三缺失条件宏均值、最差tile/条件；不把缺失排除在主要能力报告外。旧14条件已被反复查看，后续都称开发条件。

额外锁定4个仅作压力诊断的开发条件：rgb_down4+aux_zero；rgb_down4+aux_noise_std010；中央水平1/4高度DSM缺失带（y=floor(3H/8)至floor(5H/8)，其余可用）；aux_shift24（沿既有aux_shift8的方向/边界实现只换幅度24）。它们不参与checkpoint选择、门槛调优或选赢家，不称独立地区泛化；具体实现/随机键须在首个训练前写入配置与测试。

## 预先规定的去留条件

以下为新D25建议门槛，不回改D24；实现定稿时原样锁定，不能见结果后放宽。

- 能力底线：候选clean至少达到历史D1−0.1pp=86.970670；相对同轮P0，available综合、全缺失及三缺失宏均值分别不低于−0.1pp；旧14条件任一tile fg5不低于P0−0.3pp。底线用于筛选，不能写成统计非劣效结论。
- 实用增量：相对所需匹配控制，满足“available综合≥+0.2pp且缺失宏均值≥−0.1pp”，或“缺失宏均值≥+0.5pp且available综合≥−0.1pp”。所有能力底线同时成立。
- H1：P2必须同时对P0/P5达到增量条件；若P5同样有效，归因参数/通用解码变化，撤回状态专属解释。
- H2：P3须对P2/P7达到增量条件；P4对P0作无分头验证。若冲突极少或P7相当，不声称方向冲突解决了问题。P3只胜P0但不胜P2/P7，只能保留组合表现，不写独立投影贡献。
- Pair修正P1按D24原Pair匹配规则检验：对P0综合≥+0.2pp、clean≥−0.1pp、tile/family≥−0.3pp；不以D25新底线倒改旧假设，不扩大预算挽救。
- 减害另判：沿D24九种available条件、固定R0的同口径harm至少降低10%、rescue至少保留90%，并报告自身光学参照；否则不声明负迁移机制已证实。
- 失败后关闭该预算下具体实现，不自动加步数/lambda/随机种子。仅普通训练有效就保留工程强基线；最多两条通过假设另立seed17/2026及真正独立数据协议，才能推进确认。不用大量像素数伪充独立样本，不报告本轮p值。

## 执行与停止

建议GPU0 P0→P2→P4→P6；GPU1 P1→P3→P5→P7。两张H10080GB、RAM/磁盘充足沿用；nohup，所有快照/log/cache/checkpoint/轻量归档在/home/jovyan/zzx下新的D25对应目录。正常job估时，不作资源探针。以D24单组约28–33分钟为参照，本轮8组含额外梯度计算粗估3–5小时，非完成承诺；每job6h硬上限，技术失败留证并继续其他组，不自动重试。

D25执行入口和新模型已实现，12项本地CPU检查PASS；五入口与Python3.10语法检查通过。尚无服务器启动观测。已完成必要行为检查：真实配置Pair改变loss/梯度；L_present+L_missing与原CE相等；投影符号/零梯度/方向和norm-sham；局部缺失像素精确回退；两头及共享参数梯度范围；恢复绑定。现在直接按[D25固定版本nohup命令](D25_EXECUTION_20261002.md)使用已知双卡条件执行，不重新测资源。

实现细化：P1单独计算冻结R0教师，其他组不增加无效教师计算；相同更新预算/数据流，实际成本另记。梯度每100步采样，4压力条件的冻结参考在本次shared_reference正常推理并缓存复用，不新增训练，非资源审计。
