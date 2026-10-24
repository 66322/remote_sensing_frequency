# 下一轮双卡实验规划：Phase 1.5 可恢复性分解
日期：2026-10-12；依据分支头：37353e1b8b7a51c5beddac8822c48268fa3db526。
状态：PLANNED_ZERO_TRAINING_AWAITING_IMPLEMENTATION_AND_SMOKE。这是一份具体计算与决策规划，不是服务器登记/运行证明。

## 1. 决定、来源与研究问题
用户要求结合最新结果、Phase 1.5 审查意见和论文思想，规划至少一天的实验；允许 GPU0、GPU1，超过一天继续；随后明确“目前不用管释放单卡问题”。因此预留双卡24–48小时计算窗口，不设24小时终止，不开发新的单卡释放逻辑。服务器由用户执行、无SSH；全过程产物位于 /home/jovyan/zzx 下新实验目录。

研究主线保持 RGB–DSM 双向条件互补与退化/缺失分割；任务驱动恢复旁支。当前唯一下一科学问题为：**固定模型在局部RGB缺失时的剩余伤害如何分布，DSM的对应信息贡献多少，以及现有专家有哪些可被观测信号识别的互补空间？** 本轮是RGB侧机制诊断，不能据此宣布双向方法成立。
可靠性/路由仅为条件候选；残差上下文适应也不是默认必做。五项诊断完成后再选择下一训练问题，不因某个漂亮中间结果提前转向。

## 2. 现有证据怎样约束下一轮
口径：Potsdam fit12/重复开发Val2(3_11、5_10)，seed42，native512/stride256、NoBoundary pooled fg5；D15 legacy DSM-only另有Train16训练史。详细运行ID、配置/绑定和原件见[关键复核](../experiments/LATEST_RESULTS_KEY_REVIEW_20261012.md)、[Post-T](../experiments/POST_T_PAIRED_V2_RESULTS_20261012.md)、[Structured](../experiments/STRUCTURED_FAILURE_V0_RESULTS_20261012.md)。

- 实验已验证：S1主PE=+0.122522pp，CI[-0.307733,+0.592930]；原Structured假设仍NO_SUPPORT_THIS_PROTOCOL，不扩20个realization救旧gate。
- 实验已验证：RGB-only PE=+3.119077pp且20/20正；S1缺失区damage约21pp，RGB-only约56–62pp。跨模型训练史不匹配，不能将差额全部归因DSM。
- 实验已验证：R16块缺失下DSM特征C−Z=+4.009563pp、C−S=+9.114377pp；是固定模型敏感性，不能搬成S1-0结论。本轮输入DSM干预与旧特征干预也不是同一估计量。
- 实验已验证：R16−H16=+0.348562pp且两tile正、局部门槛通过；总gate失败来自5/6 E条件相对R0底线，不是clean指标已下降，也不是R-H无效。R16自身8k→16k仍+0.618217pp，独立预算比较不支持盲目延长当前配方。
- 实验已验证：S1-3旧RGB_U+4.102pp，与M000_context新mask内−11至−18pp的统计支持/拓扑/适应史不同；必须同输入统一评价，不能仅凭“context”名称选方法。
- [D27](../experiments/D27_FINAL_REVIEW_20261003.md)的路由集中、[D30](../experiments/D30_COMPLETED_REVIEW_20261004.md)的保护/恢复取舍，要求先证明专家相对优势可识别；不能重新堆同一gate或恢复损失。

## 3. 审查意见的采纳与修正
沿用[主协议](PHASE_1_5_RECOVERABILITY_20261012.md)，本文件作为执行前v1.1澄清；冲突处以本次明确澄清为准，原版本可由上述父提交追溯，尚无新科学数据。

1. 接受E空间profile、A双模型干预、D完整专家池、条件胜率、DSM-only来源与raw/smoothed分报。
2. 一个realization只能测工程时间/一致性，不能估跨realization方差或据此删5%档。
3. B只使用pixel族，因此PE(r)=NA。分别报告整图D_NB(r)、缺失区D_M(r)、固定公共M5区D_core(r)。mIoU差/r不是每像素伤害；真正像素量为(new_error−recovery)/valid_count。比例曲线形状不单独证明补偿饱和。
4. A使用同DSM条件的clean RGB作为匹配参考：D_j(M)=Score(clean RGB,DSM_j;M∩NB)−Score(masked RGB,DSM_j;M∩NB)。另报相对intact clean的总损伤。否则DSM自身损伤混入RGB缺失效应。
5. shuffle均是分布干预，最多支持对应敏感性；不能从两个shuffle差值唯一识别局部/全局因果机制。“差异不显著”不等于两干预等效。
6. crop-shuffle明确为**512网格块的位置置换**，不是512 crop内逐像素打乱。6000边长不能整除512：按相同(h,w)形状分组置换（512×512块、512×368条、368×512条、368×368角），边缘不padding再裁切，保持原tile像素严格双射。角块可能不动，报告固定点比例。tile-shuffle为全像素双射；映射固定跨realization，两模型共享。
7. 旧Structured源码JOBS编号实际为1–20。smoke固定realization_id=1、tile=3_11；不得寻找不存在的0或补造第21个mask。
8. Oracle主量为**完整NB fg5 pooled得分**，按realization先池化两tileCM再算，四族分别汇总；主决策使用四族均值H_NB，保留2/6pp设计阈值。缺失区H_M及healthy区另报，不能把H_NB与21pp缺失区damage直接相减。另报相对最佳固定单专家的增量，避免“已有一个更好模型”误判为动态选择价值。
9. any-correct oracle是固定expert池的正确率上界和乐观mIoU诊断，**不是全局最优mIoU/Bayes上界**；全错处回退S1的误分类分布可能非mIoU最优。patch oracle优化correct-count也不保证最大mIoU或单调排序。小headroom仅约束本expert池，不否定所有未来表示学习。
10. 拼接不会凭空产生额外CM误差；没有空间惩罚项的mIoU只统计所选标签。seam平滑的差额是后处理敏感性，不能直接命名“边界伪影占比”。raw主结果、局部平滑辅助保持。
11. E保留signed净damage及新错/恢复计数。ECI净damage分母≤0或bootstrap分母非正时记INCONCLUSIVE，不用epsilon制造比值；另报new-error-density比。单凭边缘伤害不能证明感受野不足；按类别分层与clean错误参照共同解释。
12. zero-init只保证初始化时无扰动。训练后精确clean保护需显式可用性门控/支路旁路；clean+failure混训只能提供约束，不能证明恒等保护。旧E失败也不证明clean退化。
13. 不采纳审查中无本项目证据的“seed噪声0.2–0.5pp”“router通常捕获20–40%”“本轮<2 GPU·hour”及“两个分支均可发表”的预断。

## 4. 固定实验矩阵与复用
模型、checkpoint、源提交、预处理、输入可用性语义、label mapping、NB mask都必须绑定SHA；沿旧评估执行链，不把S1-3、R16错误地包装为同一种forward。清零的位置/可用性标记采用仓库现有约定并写入manifest。DSM-only只读旧seed42；不可临时重训/改seed。若无法合法绑定，记UNAVAILABLE，五专家gate降为不完整池描述。

|模块|固定设计|主要产物|推理复用|
|---|---|---|---|
|E 空间伤害|S1-0；random/gradient/matched×20×2tile；0–4/4–16/16–64/≥64px|计数、ECI、类分层距离曲线|120旧预测，CPU复算|
|A DSM贡献|S1-0/R16×4 DSM条件×4mask族×20×2tile；另配每DSM条件clean RGB|PE、ΔPE、paired damage、类/逐tile|1280 missing case；S1 intact160可复用标签|
|B 缺失比例|S1-0 pixel，5/10/25%，20×2tile，严格nested|D_NB/D_M/D_core、净错密度、剂量曲线|25%40case复用；新80|
|C 类别分解|复用A/B/E/D；五类全报，Car−Building事前对比|int64 6×6 CM、support、IoU/recall、新错/恢复|不单独开重复GPU任务|
|D 专家互补|五expert；仅intact DSM、四mask族×20×2tile|raw拼接、pixel/128/256 oracle、条件胜率|复用S1/RGB/R16；新S1-3 160、DSM-only每tile一次|

A的DSM条件为intact、block512 permutation、pixel permutation、zero，原gradient/matched masks仍按原始DSM/GT匹配生成，不跟随干预重生成。D不将五expert×所有DSM干预再做笛卡尔积；D只解释intact DSM场景。

条件胜率固定两层：GT类/真实mask几何仅机制描述；输入DSM局部统计、预测熵、expert disagreement是部署可观测候选。S1归一化熵H/log(6)分箱[0,.25)、[.25,.5)、[.5,.75)、[.75,1]，计算点为原完整tile滑窗融合后的概率。旧worker只保存label，若无熵缓存，需S1 intact160case的**缓存补全重放**，不能假称完全零成本；预测应与原label逐像素相等。输入统计以预处理后的实际DSM计算，局部窗口9×9，reflect边界；clean两tile无GT统计的quartile定bin并在科学计数前锁定。不得看correctness再改箱。每箱按tile/realization保存支持数、专家正确数、胜率和差值，不把像素数当独立n。

## 5. 资源账本与双卡安排
单位case=一个模型在一张完整tile、一个输入条件的native推理，不是一个crop/训练step。

假设旧S1/RGB预测及mask可读且绑定正确：
- A新增1120 missing case（1280−旧S1 intact160）。
- B新增80。
- D补S1-3 160、DSM-only 2，共162。DSM-only对RGB输入严格不变后，复用两张预测评价所有mask。
- 匹配clean参考：A最多新增14（16−旧S1 clean2），S1-3再2；DSM-only已在上项。合计16。
- 核心新增1378；S1熵缓存补全最多160，**本次按1538次计费**。已有合法熵或clean缓存可少做，不计为新增科学样本。
- 旧缓存缺失时只补缺失绑定，不重新生成mask、不重启旧队列；登记manifest列实际缺口及总数。CPU计数/组合不会另算GPU实验。
- 合成CPU检查与真实smoke开销另记。科学5项全部0 optimizer updates、0新训练、0新训练seed。

两lane动态取尚未完成的依赖就绪case，按model+tile小批成组减少模型加载；不能将S1永远绑GPU0/R16永远绑GPU1。交替realization分配，并以smoke同case跨GPU校验确定性。E/C/聚合由CPU并行；模型只在实际lane装载一份。全量前同时核原队列complete/无活跃锁，幂等登记新目录，不重复enqueue。

时间敏感性（不含加载、写盘、CPU统计）：
|平均完整tile推理秒数|1538case GPU小时|两卡理想墙钟|
|---:|---:|---:|
|60|25.6|12.8h|
|120|51.3|25.6h|
|180|76.9|38.5h|

因此**预留24–48小时，超过48小时仍按固定清单继续**，并非保证至少实际占用24小时或一定48小时完成。若缓存充分提前完成，不重复计算填时长。若smoke明显更慢，报告修正ETA，不能删条件/减少realization。

建议相对排期（从工程包通过且实际启动起，不把写代码时间算已运行）：
- 0–2h：源绑定、合成known-answer、单realization真实smoke、两卡同case一致性；CPU E准备。
- 2–16h：优先A，两卡均可拿S1/R16工作；B/D可在各自前置参考完备后穿插，避免整阶段空卡。中间科学分数不改变队列。
- 16–36h：完成剩余A、B、S1-3/DSM参考及熵缓存补全。
- 36–48h：长尾推理、C/D/E统计、轻量打包、离线复算；以上阶段可以重叠，非硬截止。
- 24h作一次完整性/剩余ETA检查；未完成继续，不自动加训练。
nohup、stdin=/dev/null；代码快照/plan/job状态、PID、日志、预测、分块临时统计均在/home/jovyan/zzx对应新目录；不写/tmp。

## 6. Smoke与验收
在主协议12类检查上补：
- 使用真实编号1，旧mask count与SHA；两GPU相同case exact label/CM。
- 等形状块置换完整覆盖及逆映射；DSM多重集合一致；干预映射跨模型/realization不变。
- A匹配clean及共同clean两套对照、B支持区固定/变化分开。
- entropy由原概率定义、label replay exact；DSM-only RGB不变性。
- oracle raw输出来源、全错回退、patch正确计数tie、缺失区/整图分母、极端ECI NA。
- input stats无GT、correctness统计才读GT；无优化器/反传/参数写回。
任一技术失败HOLD保留原件，不自动重跑失败配方。修复版本后才重新工程smoke，失败不能被标为科学负结果。新源绑定不合法时不静默删expert或替换权重。

必须保留：case配置/源SHA/ckptSHA/predSHA，int64 6×6 CM，逐类分母，class×distance计数，五expert联合正确bitmask与误分类计数，逐tile/realization结果；大预测留服务器，GitHub上传轻量原件清单/大小/SHA及报告。5000 paired-realization bootstrap同一ID同步所有模型条件，分tile与pooled同时报；20个mask不是20个独立地理样本。禁止像素级显著性伪重复。

## 7. 一轮结束后的去留与下一训练草案
这是条件性设计储备，**不是本轮队列**；不因时间到一天自动开始。

|证据组合|下一动作|
|---|---|
|E边界集中，A对应干预明确，现expert互补较小/难识别|评审“冻结anchor的局部残差上下文适应”；小oracle本身不证明可训练恢复一定存在|
|H_NB≥6pp，且部署信号下两tile专家相对偏好可重复，优于单一专家的空间也存在|评审固定专家、预测级小router；先拆专家质量与选择学习，避免D27共适应/塌缩|
|2–6pp或legacy DSM限制明显|保留灰区；只在确有决策影响时单独设计matched DSM-only对照，不能后验换池救旧gate|
|伤害均匀、五专家均错占比大、DSM干预不能解释|停止边界/routing承诺，评审表示/跨模态知识学习或收缩问题；不默认生成模型|
|统计支持不足、两tile冲突|报告INCONCLUSIVE，不扩mask/seed找正|

若选择残差适应，下一轮建议四个同预算新训练（每组8000步、seed42、共32000更新；仅设计草案）：
1. P0：同容量pointwise residual适应，普通分割CE，作为新匹配控制。
2. P1：同容量空间context residual，替换P0的空间信息范围；主比较P1−P0。
3. P2：P1的DSM空间内容打乱控制，训练/评价控制定义需独立冻结；验证增量依赖真实对应信息。
4. P3：同总参数预算的小late-encoder adapter＋interface（重新分配参数而非加大容量），对照P1；借鉴Post-T深度线索。
全组同起点、同batch流/退化/优化器/LR；clean＋RGB failure＋DSM failure＋joint混合；anchor冻结、支持外精确保护另测。合成known-mask与无oracle部署条件分报；不把GT mask送入部署router。新主候选事前指定，固定8000主比较，checkpoint不得在压力结果上重选。保护clean/最差条件/双向收益及效应阈值在该训练协议中冻结，不能借用本轮2/6pp oracle阈值。
若选择routing，则另立静态/规则/动态/空间打乱四对照；同一冻结expert池，不同步训练expert与router，不将本方案与残差四组一并开跑。

## 8. 文献如何进入，而不是直接照搬
定向原文核对见[方法候选备忘](../literature/PHASE_1_5_METHOD_CANDIDATES_20261012.md)：
STARS用于解释共享/特有与翻译可选机制；TokenFusion用于空间替换假设；PDF用于校准及相对可靠性；SimMLM提供缺失与专家训练参照；ControlNet仅借鉴冻结底座/零初始残差；sensor-failure benchmark提醒局部缺失、整体缺失、噪声要分开验证。本轮不复现全部网络、不换骨干、不堆频率/生成模块。文献不是本项目增量证据。

## 9. 当前交付边界
已完成：结果与审查综合、执行前协议澄清、计算账本、双卡排期、文献映射、后继决策草案。
未完成：新评估器/调度器实现及测试、服务器smoke、登记和科学结果；不得给不存在的enqueue命令或称GPU已启动。
下一可执行工程工作：按上述固定清单复用Structured native评估和缓存，实现Phase1.5独立包及smoke，然后由用户终端执行。用户本次资源授权不重复询问；实际服务器执行仍由用户完成。


## 2026-10-12落实更新
用户“按上述规划进行”授权后，已实现[独立执行包](PHASE_1_5_EXECUTION_20261012.md)，20项合成CPU/13新Python语法通过。当前READY_NOT_REGISTERED，实际服务器smoke/GPU科学结果仍未取得。此前“未实现”段落为规划时历史，立即操作以执行协议/current入口为准。启动会自动验收真实smoke再接续全量，不派发任何训练；seed/模型/统计设计与24–48h资源账本保持，新增工程说明熵为softmax(mean stitched logits)，zero为present_zero/dm=True。
