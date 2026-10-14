# Phase2.4诊断与条件Phase2.5配对头实验规划（2026-10-14）

状态：**IMPLEMENTED_CPU_CHECKED_AWAITING_SERVER_SMOKE**。用户随后明确要求按规划安排具体实验；执行包与CPU检查已完成，服务器尚未登记或启动，真实CUDA/IPC/吞吐仍待smoke。[冻结工程口径与入口](PHASE_24_EXECUTION_20261014.md)，[原规划归档](../history/20261014_before_phase24_execution/PHASE_24_PLAN.md)。资源窗口GPU0/1至少预留24小时，建议预留24–48小时；未完成继续，不设24小时硬截止。实际耗时须用新执行包的真实流水线基准更新，不靠增加seed或无意义重复凑时长。

## 1. 单一研究问题、路线角色与证据边界

主线仍为RGB–DSM条件互补与退化/缺失分割，任务驱动恢复是旁支。本轮问：**匹配专家中，DSM的条件补救能否被可部署信号识别，同时避免损伤强RGB能力？** 先分离专家能力、校准/标度、融合拓扑及融合头训练分布的作用，再决定下一轮小头训练；不重新训练专家、不改骨干、不重启原B1/B3、不追加训练seed。

本轮所有结果继续属于Potsdam Fit12/Val2（3_11、5_10）、seed42的开发证据。Val2已多轮使用，互换tile训练/评估只降低本轮选择泄漏，不能升级成独立泛化证明。Test6、held4、final/test仍不开放。20个mask realization和海量像素不是20个独立场地或独立训练重复。

事实来源：[Phase2结果](../experiments/PHASE_2_RESULTS_20261014.md)、[原件验收](../../records/phase2_review_20261014/verification.json)、[门禁复算](../../records/phase2_review_20261014/gate_recomputation.json)。运行research_phase2_matched_20261013T151120_1310582，执行e5641e07，上传dc335e0d；最后已验收完成记录2026-10-14T00:39:03.210695+08:00。核心4训练48k，B1/B3没有训练，不能写成动态模型训练失败。

### 已核验结论与待检验机制

|内容|证据/数值|本轮处理|
|---|---|---|
|实验已验证：匹配诊断互补|RGB-fault oracle−bestFixed=18.4441pp；DSM-fault=3.6653pp|保留为GT辅助诊断差，不能直接承诺可部署收益或数学上界|
|实验已验证：B2相对bestFixed|RGB-fault +4.2481pp；DSM-fault −7.6092pp|oracle−B2分成互补差与融合回归；不把全部残差叫未利用互补|
|实验已验证：clean损失|RGB86.6343，DSM62.4805；equal-logit average84.8403，B0 84.3712，B2 84.2793|弱DSM可能污染融合是待检验机制，需正确性流/标度干预支持|
|实验已验证：固定熵规则不满足原双向门禁|RGB方向+15.0541pp，DSM方向−0.4779pp|原L失败和B1/B3停止有效；不据此否定全部可靠性信号|
|实验已验证：后半程clean增益小|8k→16k RGB+0.0615pp，DSM+0.0663pp|不继续拉长固定配方；不宣称全局收敛或8k永久足够|
|代码已实现：训练方式|两个不同模态、同seed42专家；专家clean训练，融合头mixed训练；融合头训练时专家冻结|不存在本轮“DSM梯度破坏RGB骨干”的执行链；旧C-OO等异协议分数不能作因果锚点|

主分数沿用NoBoundary mIoU_fg5：每个条件先池化两tile的int64 6×6 CM，再对条件宏平均；Full、逐类、逐tile、ROI、healthy、observed为诊断。引用方向分数时不得把总体P-U的RGB77.5036误当RGB-fault方向分数。原average是equal-logit mixing；probability mixing另立系统名称。

大数组已于2026-10-14T12:13:25.974504+08:00按用户授权退役：35,910文件、清单预计断链752,849,031,168 bytes。保留原CM/轨迹/执行快照/配置/必要权重/输入及L tail坐标；普通val/head cache及compact数组不能假定仍在线。下面需要confidence的新诊断只作有范围的再推理，不恢复旧大缓存；这不是失败配方重跑。

## 2. 实验清单与依赖

|编号|目的与操作|规模与预算|资源/依赖|
|---|---|---|---|
|D0 旧计数复用|gap分解、专家错误重叠、逐类独有正确与共同错误、既有RGB→fusion损伤/补救|复用原16k证据，不增加专家前向|CPU；与预检并行|
|D1 冻结专家联合诊断|一次paired forward同时统计RGB、DSM、average、B0、B2；错误流、置信度、类别/空间结构|clean2+P-U640=642 case；先12个真实case等价/资源smoke|GPU0/1共同动态队列，CPU流水线|
|D2 校准与部署探针|两次source→target fold；锁定温度、混合系数和小logistic后算target完整CM|642个目标case各在所属target fold只算一次；同次前向算所有锁定系统|CPU拟合与GPU目标评估；依赖source样本/参数锁|
|D3 扩展端点|对D2锁定系统验证P-M320、dose160、ordinary42|增522 case；与642组成原1164面板|D2后；同次前向复用|
|T0 clean头分布对照|新B0-clean对原已完成B0-mixed，隔离头训练分布|1个小头×8k；旧mixed不重跑；不动专家|验收流/初值绑定后可作独立低优先任务|
|T1/T2 保护型配对头|RGB-anchor信号残差与同容量无信号控制|2个小头×8k，成对登记；仅信号可部署门禁通过才进入|GPU0/1，各一臂；相同样本顺序|
|T3 DSM统计错配控制|确认T1提升是否需要DSM局部结构信号|条件1个小头×8k；只错配统计特征，不错配DSM专家图像/标签|T1/T2通过且DSM统计确有贡献时|
|E 最终面板与收尾|全部已进入的新头在同一paired forward上评估；原参考CM直接复用|1164 case/已进入头集合，非每头各重复专家前向；原始计数离线汇总|双GPU+CPU；轻量上传回读后回收临时量|

核心诊断为D0–D3；T0是可解释训练分布的一个新对照，T1/T2/T3有明确门禁。**最多4个新小头、32k新更新，0个新专家训练、0个额外训练seed**。温度/logistic等CPU参数拟合单列拟合账本；“零分割训练更新”不能写成完全无拟合。不得把以上条件预算视为当前已授权启动或已注册的实验。

科学面板、mask坐标、realization1–20、ratio、zero/down4和普通退化继承Phase2原plan/mask manifest，生成规则与SHA锁定。新资源优化不改变退化/增强/精度/批次科学条件。技术失败保持失败回执，不自动换配方或重新开始。

## 3. D0：先复用能直接重算的原件

1. 采用同一oracle优先序、同一面板定义分解：
   oracle−static=(oracle−bestFixed)+(bestFixed−static)。
   RGB方向B2−bestFixed=18.4440903886−14.1959471613=+4.2481432273pp；
   DSM方向=3.6652634677−11.2744662682=−7.6092028005pp。
   “bestFixed”必须沿用原协议在方向面板上的固定专家选择；不能偷偷改成逐condition最佳，再沿用上述数字。
2. 用CM对角线按GT类别重算共同/独有正确：
   bothCorrect=TP_R+TP_D−TP_oracle；
   RGBunique=TP_oracle−TP_D；
   DSMunique=TP_oracle−TP_R；
   bothWrong=N_true−TP_oracle。
   校验非负及四项和等于N_true。按tile/方向/类/ROI汇总并给有效分母；稀疏或常量边际的phi相关标NA。
3. 复用原transitions的RGB→candidate rescued/harmed。它不足以恢复完整(Rcorrect,Dcorrect,Fcorrect)联合流；不能用边际CM捏造这一联合计数，缺项由D1生成。
4. “专家disagreement内bothCorrect”逻辑上不可能：两者预测类别不同，不能同时等于GT。四格先在全部有效像素统计，再对子集报告。共同正确却被class-dependent fusion翻错可发生，需在全体联合流单列。

### 对照性alignment null，不能作研究生死门禁

像素内交换专家正确性标签保持max(correctness)不变；若专家边际也保持，union accuracy−bestFixed也不变。该re-deal按原建议执行无效。两个专家一次确定性分割也没有LLM多次随机解码那种估计设定。

可作附属CPU诊断：在tile×condition×GTclass内固定RGB/DSM的**完整6类预测边际**，跨像素重新对齐一个专家，采用固定行/列边际的6×6列联表抽样（多元超几何），1000次；按RGB优先的原oracle规则重建null CM，再按原指标池化/宏平均。只交换二元正确性不能重算mIoU，因为bothWrong时错误去向影响IoU。

第一版仅对NoBoundary/all的原CM作该非空间null；它描述固定边际下错误重叠的参照，不估计“不可恢复噪声比例”，不输出以数百万像素作独立样本的p值，也不以观测是否落入区间关闭路线。若D1显示空间聚类影响解释，再用其块联合计数做预先声明的block条件参照，限定少量案例。统计模拟RNG与训练seed分开登记。

## 4. D1：正确性流、标度与空间结构

两专家固定16k endpoint，加载必要旧B0/B2最终头。原输入/权重manifest首次集中验证，并建立只读共享绑定，避免每个分析进程重hash同一批大输入。

每个case一次 paired expert forward，同时取得旧average/B0/B2输出。旧系统继续原512/stride256/529窗、低分辨logit插值/拼接规则。主微批8、原Torch/TF32/精度设置先锁定；增微批仅在12case等价检查通过后另记工程版本。smoke固定选原面板2clean、8个P-U（两tile×两方向×zero/down4，pixel/realization1/ratio25）及2个P-M（3_11 RGB缺失、5_10 DSM缺失，同pixel/realization1/ratio25）。P-M项提前完成后复用于D3，不增加面板或重复计数；两GPU各6case。

直接累计以下轻量原件：

- int64 6×6 CM：Full/NoBoundary；all/missing/healthy/observed；逐tile/类/系统。
- (GT,R,D,F)联合预测计数及(Rcorrect,Dcorrect,Fcorrect)流：RGB独有正确被fusion损伤、DSM独有正确被采用、共同正确被损伤、共同错误；同时给数量和条件比例。
- RGB/DSM置信度直方图、固定15等宽ECE bins、NLL、Brier、margin、中心化logit norm、错误但高置信比例；分clean、两故障方向、GT类及预测类报告。ECE依赖分箱，不单独据它判断校准优劣；NLL/Brier为主要标度证据。
- 按固定256×256坐标块累计harmed/rescued、有效像素及局部DSM统计，诊断空间聚类；再按ROI边缘/内部拆分。不保留全图伤害热图，最多登记12个ROI裁剪用于核对，不访问新tile。
- 一次扫描/联合编码推导多系统CM，避免按系统×scope×region重复扫描6000²数组。GPU整图拼接/计数先与CPU参考比对int64结果；不通过则保留CPU向量化实现，不静默换指标。

**校准的概率定义要锁定**：整图原输出使用窗口logit之和，其幅度受coverage影响。校准诊断采用覆盖次数归一的mean-stitched logits再softmax，避免把重叠窗数当自信；旧系统hard prediction仍按旧执行链复核。mean-window probability是另一决策类，不与softmax(mean logits)混写。旧L的窗口熵定义保留，不把新像素置信度倒写成原L证据。

诊断样本只存本轮拟合需要的logits/可部署features、GT和block/采样权重：全轮最多2,000,000条，RAM常驻上限1GiB，分层reservoir确定性采样，记包含概率和重复坐标/block。分层过采样必须用逆概率权重恢复校准/损失分布。原CM与直方图全量统计，样本只辅助拟合；不可把sample指标当全图结果。源fold内部拟合/校准划分采用2048×2048空间块（不是上述256统计块），重叠window及同坐标的不同mask放入同一组；仅采样距内部块边界至少512像素的位置，避免局部窗口泄漏。

部署输入不含GT、真正故障mask、direction/family/ratio标签或tile ID。已报告availability只在P-M/known-missing合法使用；P-U不能把隐蔽损坏mask当输入。

## 5. D2/D3：cross-tile校准、alpha曲线与可预测性

Outer folds固定：3_11拟合→5_10评估；5_10拟合→3_11评估。每个tile的最终评估只用另一个tile锁定参数，目标结果不能用于改模型/阈值。内部source采用2048×2048空间块分训练/校准两半，按固定coordinate hash分组；相同坐标所有mask归属一致。源训练块拟合，源校准块选超参；guard及实际支持量写回manifest。

### 校准/静态对照

- 原equal-logit average、RGB-only、DSM-only、旧B0/B2为固定参考。
- 每专家一个正温度T，范围[0.25,4]，初始化1，source clean代表性样本上加权NLL拟合；不作GT类依赖或target调参。另列source mixed拟合为敏感性诊断，不参与主门禁。
- 主混合为z_alpha=alpha*z_R/T_R+(1-alpha)*z_D/T_D，alpha预先固定{0,0.25,0.5,0.75,0.9,0.95,1}。与T=1未校准曲线配对，RGB端点必须存在。source校准块按保护约束选择alpha；无合格alpha返回RGB，不能强制取小于1。
- probability mixing是明确命名的次要对照，不与原average等同。source sample可画探索曲线，主target全图评估只用已锁定alpha/参数，不能在target曲线上重选alpha。
- 正温度不改变单专家argmax；若出现改变先查数值/拼接错误。校准可改变混合/选择，不能将校准声称为单专家分割精度提升。

### 极小部署探针

主探针为L2 logistic，备选depth1 stump只作预先列明的敏感性对照。输入组固定：两专家entropy/maxprob/margin/中心化logit norm、预测disagreement、DSM mean/std/gradient、RGB zero-fraction以及合法availability。各量归一参数仅source训练块拟合。GT class只作评估分层；可输入专家预测类，不能输入真实类别。

标签定义为“DSM独有正确”正类，负类保留RGB独有正确和bothWrong；不能只在oneCorrect子集训练却忽略部署时bothWrong。same-prediction没有选择收益，默认RGB。source校准块从固定阈值{0.5,0.7,0.9,0.95,0.99}选保护型采用阈值，L2候选{0.1,1,10}；没有合格解则RGB回退。AUPRC/ROC/校准仅诊断，进入训练须依据实际target完整CM的净收益/损伤。

校准与探针的主部署操作定义为**post-stitch mean-logit决策**：一次原专家拼接后施加锁定决策；旧B0/B2仍原window-head链。二者决策拓扑不同，结果分开命名，不把探针成功当原B1已验证。探针的拟合/推理feature定义一致；后续T1/T2的新拓扑也显式登记，不假定非线性gate与拼接可交换。

D3追加的P-M/dose/ordinary只评估D2锁定系统，availability fallback逐像素精确核验；同一专家前向产生所有已锁定对照输出，绝不为了每个alpha/头重复整套backbone推理。source/target参数都锁完后，D3可由两GPU共享队列完成。

### 新的开发入场条件（不修改原Phase2 L）

可部署信号门禁只针对新“RGB-anchor保护”假设，评估双方向：
- RGB-fault pooled增益相对**source选择、target评估的最佳静态参考**至少+0.5pp，两个target tile分别>0；
- 全P-U增益至少+0.3pp；
- DSM-fault、clean和healthy相对RGB保底/同fold静态参考退化均不低于−0.2pp，两个target tile分别满足；参考若含合法缺失先按availability回退；
- 每个family×damage最差差值不低于−0.5pp，P-M fallback exact；
- 两fold采用率、净补救与RGB正确像素受损率分别报告，不能用总体分数掩盖direction回归。
比较集包含RGB-only和校准静态mix；不给候选一个比RGB更弱的保底。条件bootstrap按同realization配对，仅解释固定两tile下的mask扰动，不以bootstrap CI替代独立场地复验。

结果出口：
A. 校准/静态mix已满足保护与收益：优先报告低复杂度解，T1/T2不为凑预算启动。
B. 校准不能解决但logistic具有实际跨tile收益且保护通过：登记T1/T2成对训练。
C. 当前特征/小模型不具备跨tile可用收益：停止本轮这一观测-决策类，不自动关闭所有RGB–DSM互补问题、换主线或追加seed。空间/类别线索若只是相关性，保持待检验状态。

## 6. 条件Phase2.5：真正的训练对照

### T0：头训练分布对照

B0-clean复用原B0的8个参数、初值、优化器/LR/8k预算、phase23 base crop/GT stream与seed42；唯一处理差异为输入保持clean，旧B0-mixed已完成，直接复用其权重/原CM/轨迹。新生成base crop token须逐step匹配旧batch_hashes，初始化匹配4a3c4baf...，GT/augmentation流与混合损伤处理明确分离。专家冻结，不能用此比较解释专家表征被梯度损伤。

若不能复现原base stream/初值，则标不匹配、保持待核验，不能自动再跑旧mixed补对照。此历史配对控制只检验本次同seed处理差异，不构成独立重复。

### T1/T2：RGB-anchor残差 vs 同容量无信号

两臂固定专家16k、Fit12、seed42、8k endpoint、相同phase23 base stream/损伤/availability/LR/物理batch16；小头FP32，两臂MLP规模/参数量/初始化相同。主输出：
z=z_R+tanh(h_theta(s))*(z_D-z_R)。
最后线性层为零，故起点严格等于RGB，tanh导数在零处非零。**这是允许负系数的有界有符号残差，不冒称始终非负的凸混合gate。** 采用固定0.01*mean(abs(g))保护正则，两臂相同；阈值、正则不看target重调。须真实梯度smoke验证更新可发生；不能使用零点死梯度的ReLU门硬称可训练。

T1输入D2锁定的部署特征；T2同网络把新增信号槽置零，只保留合法availability，并仍用同一R/D logit差。两臂共享主数据，区别只为可部署信号；这比较特征可用性，不将名义参数相同写成有效函数空间完全相同。实际post-stitch推理与crop训练接口、低网格到全图操作需在执行包冻结；若实现改成window-gate则必须新命名并重新跑部署等价检查，不能沿用post-stitch探针结论。

训练在crop内单窗上产生专家logit，窗口覆盖归一规则与部署输入一致；输入尺度差/窗口拼接拓扑的泛化风险作为新头实际端点评估对象，不能仅由D2推断T1会成功。研究仍双方向评估，非对称操作是候选解法，不能隐含改写研究定位。

T1/T2只固定endpoint8k，不用两张Val2反复早停/改年龄。保存训练损失、gate分布、梯度和相同batch哈希；轨迹诊断4k/8k，两臂同时报告，主结论不挑更有利年龄。T0或T2无收益并非失败异常，不重训救配方。

### T3：DSM统计错配

仅在T1达到上述保护条件，且T1−T2≥0.3pp且两个tile均>0时进入。固定专家原图与标签，只将DSM mean/std/gradient统计按同crop内固定非零偏移打乱；其他feature不变。同初值/流/预算。控制可能产生统计分布错配，因此“真实DSM统计帮助”只能结合错配与消融判定，不能称最终因果机制已证明。

### 端点评估与去留

所有已进入头在原1164面板同批生成，原系统指标直接复用并用12case数值smoke桥接。采用保护门禁；signal相对无信号控制需≥0.3pp，两个tile分别为正；若只有补救增益而clean/DSM方向不保护，方法不接受。4k轨迹只解释训练稳定性；不因loss继续下降自动延长预算。

新增多seed/独立数据检验放入将来确认性阶段，须明确开放和单独登记；本轮不自动加两seed×三模型。D0 null或小margin差也不能单独证明所有router无效。

## 7. 资源规划：先减少重复处理，再提高并发

### 已观测历史与真正瓶颈

[资源/方法审计](../../records/phase24_planning_20261014/resource_and_method_audit.json)绑定上一轮原件。Phase2于2026-10-13 15:13观测effective_cores192、约1.85TiB可用；analysis_workers=16，每worker OMP/MKL/BLAS=1。这不是整台只用一线程。B0/B2各1164case计数完成跨度约2.44/2.58小时，最后forward progress到counts中位约30秒、p95约37.5秒；包含排队/拼接/写盘，不能当纯CPU服务时间。Phase1.5原单进程后由两进程、向量化及驻留复用加速，97个剩余case约1595秒；提速不能全归给线程数。

代码中反复输入hash、全图decode/stitch、各scope/region扫描和case落盘是改进点。不能仅依据1.9TiB主机内存，忽略实际cgroup/quota/文件系统拥堵或无限进程增加内存带宽争用。

### 拟议流水线与上限

1. 新启动先测CPU affinity/quota、cgroup有效可用RAM、GPU0/1实际空闲显存与目录可写/盘配额；历史资源不当实时值。不探其他GPU分配任务，不用SSH。
2. 原输入只读共享驻留；常驻expert/头，case动态派给GPU0/1，按完成事件异步归约，不用两卡每步全局barrier。两方向/两tile均衡穿插，长case预估调度，避免一张卡独占长尾。
3. CPU起步16分析进程，每进程数值库1线程；对同12case的RAM缓冲回放统计，比较16/24/32上限（不为调CPU重复专家前向），受实际CPU预算约束，另保留16–24核给数据/GPU供给。CPU进程×内部线程不得超配；GPU数据准备每卡4–8workers，预取4–8批。
4. 整图R/D logit、旧头输出及计数只在GPU/有界RAM中短驻留；共享内存句柄或环形缓冲传输，避免pickle整图复制。每卡最多2个待统计整图slot，总临时RAM上限128GiB且不超过有效可用内存25%，诊断样本RAM≤1GiB。实际实测峰值登记；有界内存不能被误写成全轮预计算缓存。
5. T1/T2每GPU各有冻结专家及小头；相同crop token顺序，独立运行无需逐步等对卡。每batch专家输出最后使用后释放，预取有界，不生成8000个NPZ。只在已登记消费者确实复用时小块共享，不跨尚未通过的分支囤积。
6. GPU拼接与int64 joint counters可尝试提高吞吐，但须与CPU参考逐字段一致；若GPU atomic/确定性约束不允许，保持CPU向量化单扫描。主微批8；试16/32仅工程smoke，要求硬预测/CM exact，logit容差事前声明；不通过保持8，不能静默改变科学口径。
7. 基准单列forward/stitch/transfer/statistics/queue/data_wait耗时、RSS/显存峰值、ready backlog与GPU idle reason。已有ready任务而GPU idle>20%连续5分钟报警工程排查；仅资源瓶颈调整，不换科学配方。内存队列背压优于无限预生成文件。
8. 最后一批GPU完成后CPU聚合还可能运行，状态明确标CPU收尾。若门禁必须等待且无独立授权工作，GPU空闲是依赖结果，不以无意义新实验维持占用。CPU参数拟合期间可并行D0/null、已锁定扩展case或T0，不能提前执行依赖未满足的T1/T2。

### 24–48小时安排及ETA

|资源窗口|优先任务|调度原则|
|---|---|---|
|0–2h|预检/12case等价与吞吐基准；D0旧计数审计|两卡同时smoke，各6case；CPU独立准备|
|2–8h|D1联合流/标度诊断；source样本拟合逐步开始|两GPU同一动态队列，统计边生成边聚合|
|8–16h|D2两fold锁定评估+D3补充面板；可并行T0|CPU拟合完成立即投递锁定目标；不等全部case才分析|
|16–32h|条件T1/T2、需要时T3；端点全部已进入头评估|双GPU配对训练/端点共享前向；门禁失败如实提前结束该分支|
|32–48h及以后|剩余长尾、离线核验、轻量上传回读和退役|不因24h到时强停；不为凑时间新增训练|

以上为资源预约和粗粒度完整路径预估，**不是实测结束承诺**。上一轮平均16k完整面板约2.64h只是旧pipeline的计数跨度；本轮联合计数/多个锁定系统、RAM流程、无整轮头缓存改变服务成本。12case后输出阶段ETA及范围；CPU/GPU分别估算，不能只看training remaining_hours忽略推理/分析。如果低复杂度校准已解决问题或信号门禁失败，不人为让设备空跑满一天，24小时资源窗口的授权不等于必须耗尽。

## 8. 存储生命周期与恢复

遵守[用户产物精简决定](EXPERIMENT_ARTIFACT_RETENTION_20261013.md)。新目录拟用/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase24_protected_<timestamp_pid>；本轮尚未创建。所有snapshot/records/临时量在该对应目录，禁止服务器/tmp等范围外放执行记录。

- 不落盘全轮logits、6000²逐case预测或8000步head cache。临时磁盘默认0；若实测必须溢写，启动前登记，环形暂存≤8GiB、最多2slot，最后消费者ack即unlink；超限hold，禁止默默扩为TB。
- 诊断fit样本在RAM完成两fold锁参后释放；长期保存选中坐标/采样规则/SHA、参数和聚合直方图，不永久保存百万样本。如果要独立复核可按相同绑定重新产生限定样本，不为了未知用途保留全量。
- 必留：int64原CM/联合计数/逐类/逐tile/区域原计数，histogram与calibration充分摘要、fit参数/规则、fold分组/采样权重manifest、source/input/checkpoint绑定、代码配置、预算、轨迹、完成/失败原因、资源与退休回执。大量相似小JSON可组织为分片JSONL.gz+SHA索引，避免每window创建文件。
- 轻量汇总目标≤1GiB（不含必要模型权重；若超限先审计内容）。图只保留必要曲线及≤12个裁剪样例，禁止所有case热图。长stdout轮转≤20MiB/worker，保留错误和关键进度，不能丢原始计数。
- 新头仅保留endpoint8k及待轨迹诊断的4k；rolling last_resume单份替换，不每500步无限积累。端点验收、无恢复/下游依赖后删除resume/优化器状态和4k权重，保留4k原计数/轨迹。必要旧专家/头和用户原数据不在新自动删除白名单。
- 每缓存登记生产者/消费者/reference count，最后消费后立即释放；正常、用户中断、技术失败均有finalizer/回执。失败留最小恢复/排错状态，无活消费者时回收可重建张量，不能自动再训练。
- 磁盘删除仅新运行目录预登记白名单；resolve验证位于/home/jovyan/zzx及该运行目录，拒绝symlink跳出、身份变化和活引用。保存inode去重清单及前后变化；df整挂载盘变化不能当本目录回收实测。
- 轻量原件核验/离线重算完成后上传GitHub并回读SHA，再退役依赖已释放的审查期临时物。不得为上传把整个运行目录递归加入Git；权重仅大小/SHA/服务器索引。

上述生命周期、数值等价、异常清理和预算限制必须写入新执行控制器并做真实smoke验收后，才可给用户启动命令。当前只完成设计，不能写成自动清理代码已落实。

## 9. 外部长文本与论文思想的采用边界

|建议|处理|
|---|---|
|gap分解、correctness flow、calibration、cross-tile alpha/probe|采纳，但修正disagreement bothCorrect、logit/probability口径以及缓存已删除状态|
|像素内re-deal作为唯一生死gate|不采纳；数学不变且随机解码设定不适用；采用附属跨像素alignment参照|
|“三专家只换seed”“融合端到端梯度伤骨干”|与原执行链冲突，纠正为两模态同seed、专家冻结|
|旧C-OO86.35对本轮B284.28解释2pp因果损伤|不采纳跨协议因果比较；T0保持本轮骨干/预算/流才检验头训练分布|
|margin没差→任何confidence gate都不可能|不采纳；单一统计和模型类失败只约束当前观测/决策类|
|追加两seed×三模型、8k足够永久关预算|本轮不自动派发；复现留后续确认阶段，预算小后程不等于全局收敛|
|保护强RGB、允许不对称干预|作为新候选解法，仍评估两方向；不倒写原Phase2双向L已经通过，也不隐含切换研究主线|

外部文献已核原文，使用边界如下：
- [Chen，arXiv2607.03436 v3，2026-09-27修订](https://arxiv.org/abs/2607.03436)：当前题为“What Does a Routing Oracle Measure Under Stochastic Decoding? Coupling, Scorer Choice, and Single-Commit Ceilings”，v3说明替代早期经验解释。借用区分oracle构造与可部署决策的思想；旧12–36%数字不照搬到确定性分割，不声称同样膨胀比例。
- [Cakiroglu等，Oracle Gaps in Reliability Coverage，v1](https://arxiv.org/html/2609.32996v1)：其re-deal对每prompt的多次policy响应重新分组，非像素内两个专家的一次标签互换。借用固定边际/决策类对照思想，不转用0.096/0.113作为本项目修正量。
- [Guo等，On Calibration of Modern Neural Networks，ICML2017](https://proceedings.mlr.press/v70/guo17a.html)：温度缩放是低复杂度基线，是否解决本轮融合损伤须由锁定cross-tile指标验证。
- [DarkAct，CVPR2026官方页](https://openaccess.thecvf.com/content/CVPR2026/html/Tan_DarkAct_A_RGB-Thermal_Dataset_and_Fusion_Framework_for_Multimodal_Low-Light_CVPR_2026_paper.html)：RGB-thermal低光动作识别，与RGB–DSM分割不同；只作为模态条件依赖的背景，不据摘要认定“多数融合不如单模态”已普遍证明。

## 10. 下一交接必须记录

研究阶段/路线角色、各门禁实测值与stop原因、用户授权与来源、未采纳建议、CPU/GPU最后观测时间、实测资源与ETA、原件/汇总可复算、缓存最后消费者及退休状态。计划→实现→smoke→注册→运行→验收分别报告，不从docs提交推断服务器运行。新头研究证据成立前，下一阶段大训练与确认性多seed仍未开放。
