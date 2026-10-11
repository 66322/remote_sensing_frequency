# Structured Failure v0：结合现有证据的下一阶段设计评审

日期：2026-10-11。状态：DESIGN_REVIEW_DRAFT_NOT_REGISTERED。本文是助手对用户所附规划的综合建议，不是新增执行授权或已完成的预注册。生成器、模型解析清单、真实掩码、known-answer测试与执行队列均未实现/登记；不得据本文直接启动推理。科学门槛和数值参数以下均为事前建议，实施前需完成仅依赖输入/标签、不依赖模型结果的可行性核验，再一次性冻结。

权威分支：66322/remote_sensing_frequency / rebuild-v1-protocol-20260915；本次核对HEAD=699f8f9832f0ac52f9fdfd5a670c659c4f0557b6。最后服务器查询仍为2026-10-11T18:54:08.952037+08:00：CONTENT_PRE完成，H8 GPU0、F8 GPU1各180/8000且进程存活，其余待运行。无更新的实时查询。原队列research_post_t_paired_v2_20261011T182543_3880702、执行44e4df5afbaeb603e6441e7ef14ff09f228bc027保持。

用户附件原文：[user_proposal.md](../../records/structured_failure_design_review_20261011/user_proposal.md)，SHA256 b0ecbeb430991e419059b314f59d80b5b1d83f8c96a093c1567643ac7986b57d。用户本轮要求综合分析下一阶段，未要求立即实施附件全部步骤。本文建议不触碰正在运行的代码、配置、目录、GPU或调度；未触发任何模型训练、推理、掩码生成或后继队列。

## 1. 综合判断与研究角色

建议保留附件的三个问题，但分为“已有证据再定位”和“新假设验证”：连续性/空间形态效应、DSM结构相关落点效应、固定权重下的上下文策略交互。当前F/H/R回答“哪些参数需要适应、长预算是否有效”，拟议评价回答“哪些失效布局更困难、上下文策略在这些布局下如何变化”。两者互补，评价结果不得反过来更换R16主候选或改动原门槛。

研究主线仍为RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复为旁支。Structured Partial Modality Failure是拟检验的RGB局部缺失子问题；不能仅凭一次开发诊断PASS将整个论文主线改名，也不能凭它FAIL取消所有合理方法探索。双向主线后续仍须补真实DSM方向的帮助空间与有效支持，当前DSM_U保护不等于反向收益。

|已有实验已验证的开发证据|对下一轮的作用|不能推出的结论|
|---|---|---|
|完整T五个上下文匹配对约+1.432～+1.521pp，两tile正|上下文收益已有重复开发证据，下一轮定位它对空间布局的依赖|上下文收益专属于结构化缺失，或已支持双向性|
|T7−T1仅+0.019790pp，仍落后R0 1.125243pp|移植解码初值的独立增量未成立，当前F/H/R有必要|延长旧T7或换最高分组即可成功|
|M300_context−M000_context +2.901426pp；DSM包单独交换+0.005618pp|区分专家适应位置，同时等待本轮DSM内容诊断|纯编码器机制、DSM无用或互补创新已经证明|
|T1/T7后4000步+0.334083/+0.321695pp|支持统一初值的新8k/16k配对|16000必胜，或所有模型普遍欠训练|
|S1-3的RGB局部缺失有收益，但原保护门槛失败|固定基座与局部输出保护必须保留|可以把S1-3直接作为成功方法|

数值口径均为Potsdam fit12→重复Val2 3_11/5_10、seed42、native512/stride256、NoBoundary pooled mIoU_fg5；见[完整T](../experiments/POST_T_FULL_RESULTS_20261011.md)、[机制诊断](../experiments/POST_T_MECHANISM_RESULTS_20261011.md)、[N3/S1](../experiments/POST_N3_S1_RESULTS_20261008.md)、[旧P与部分T](../experiments/POST_S1_FULL_TRANSFER_PARTIAL_RESULTS_20261010.md)。无Test6或独立泛化结论。

## 2. 必须先修正的设计问题

### 2.1 S1-3−S1-0不是纯上下文效应

两组在相同起点之后分别训练，完整专家包与融合参数已经不同，同时改变特征支持和局部输出策略。它们的差值应记为historical-system gap，只作描述。纯推理策略对照采用固定同一套权重、固定C0保留融合、仅改变B：A1B1C0 versus A1B0C0；复用已实现并已验收的M000_masked/M000_context。需要时用M333_masked/M333_context作预先指定的第二套权重复核；M333_context曾在旧16case复现R0，换新掩码后仍须重新核验，不能直接套旧分数。

固定权重、条件和支持后定义CB_theta(M)=Perf_theta,context(M)−Perf_theta,masked(M)。这测量上下文特征保留策略的受控交互，不是统计学因果中介分析，也不代表重新训练两种策略的总效应。

### 2.2 随机块与语义匹配twin承担不同任务

U-block随机位置用于CE；若为匹配S-grad的语义构成而筛选位置，该对照就不再是无条件随机。新增独立U-block-matched，主位置效应为D(S-grad)−D(U-block-matched)。U-block-random与S-grad的差另报为总体位置策略差，不能混写成“类别匹配后的结构效应”。

若U-block-matched使用GT类别直方图，它的生成属于label-assisted diagnostic，即便模型不读取标签也必须标明。GT只进入生成/匹配和评价，不能进入部署路由。S-grad本身可用DSM生成，但真实传感器故障是否偏向高梯度位置仍无现实数据证据；这是受控合成压力。

### 2.3 相同block尺寸和数量不保证相同footprint

重叠、裁边、相邻块合并、边缘距离及与512/256滑窗的相位均可能变化。需要精确实际面积、无重叠/裁剪、相同primitive清单、连通块/周长检查，另记录块间距、窗口覆盖/相位、有效标签比例等剩余差异。若整个布局并非刚体平移，措辞只能是“primitive几何受控下的落点效应”，不能称完整空间几何只有placement不同。

### 2.4 不预设连续块更有害

散点25%缺失会广泛扰动RGB编码token，也可能在valid_at这类“感受区域全有效才保留”的特征支持规则下屏蔽大量空间位置。仅作独立像素示意，4×4区域全有效概率为0.75^16，约1%；该计算不是实际模型测量。块状缺失则集中破坏并保留大片完整输入，所以CE也可能为负。CE测的是指定比例下的空间布局干预，混合距离、边界密度、有效token比例等因素，不能单凭CE给“连续性本身”作普适归因。

应记录各实际特征尺度的有效支持比例、到最近可见RGB的距离分布、完整缺失窗口比例。旧B1/B0执行位置与mask降采样都必须核对。

### 2.5 healthy区域可能为空

Healthy=not Dilate(M,8px)保留为有缓冲诊断，但对随机像素25%缺失可能几乎为空。独立像素及Chebyshev半径8的内部示意概率为0.75^289；实际固定面积掩码应直接计数。healthy分母为0时记NA，不能记0伤害或通过保护。并列报告所有未缺失区域not M、缓冲healthy、边界邻域三类分母。主保护依据原始计数和已冻结输出支持外exact，不因空集合自动通过。

### 2.6 20→40与模型“winner”都不能自动扩张

第一轮建议固定20组掩码实现，一次终点分析；它们不是20个训练seed或20个地区重复。不采用看到0.15～0.30pp就自动翻倍，结果不确定可标INCONCLUSIVE。确需40组应另定版本，说明选择影响与成本，不能将两阶段普通p值当一次检验。

当前F/H/R固定主候选为R16，不能用新掩码挑“winner”。若将来转入新掩码方法评价，最小比较为预先选定候选加匹配普通控制及R0；不能只加入获胜候选而省去F/H。H因简单而值得保留，需另行明确研究决定，不能倒写为原R16成功。

## 3. 分阶段安排与规模

|阶段|具体内容|新增训练|状态与执行条件|
|---|---|---:|---|
|Phase 0 当前队列|完整F/H/R×8k/16k、前后DSM内容诊断、原件验收|原已登记72000步|继续原队列；当前新规划不修改/插队/扩组|
|Phase 1准备|协议、解析模型绑定、生成器设计、合成known-answer测试、registry schema|0|可在本地做轻量CPU开发；不占服务器现有CPU/I/O密集资源|
|Phase 1A 核心|4固定输出系统×4掩码家族×20组实现×2tile，另清洁基准|0|640缺失输出case＋8逻辑clean基准；新代码/生成器验收、原队列退出和资源再查询后才执行|
|Phase 1B 权重复核|固定M333_masked/context跑同一冻结mask bank|0|最多320缺失case＋4逻辑clean基准；预留未登记，用于S1-3权重下的稳健性与R0参考，不事后搜索其他M组|
|Phase 1C 可选诊断|GT boundary与block-size机制研究分开|0|只在核心问题仍值得解释且另冻结范围后执行；不是第一批必跑矩阵|
|Phase 2 新训练|依据Phase 0与1综合决定最小配对|待定|本轮只列设计分支，不写入训练队列|

Phase 1A建议四系统：

1. 真RGB-only anchor：当前执行链绑定的D25 P6 DINOv2 ViT-S/14 optical_only，selected step2000；不是旧REBUILD R01，更不是Post-S1 R0。它提供单模态脆弱性描述，不与异构双模态结果直接归因融合增量。
2. S1-0完整固定基座：当前条件下的普通双模态/硬回退参考，指定为主位置效应判定模型，不再另加含混的“Dual anchor”。它只代表这一实现，必须报告特征/输出策略。
3. M000_masked：S1-0相同参数、A1B1C0、共同native支持外基座路由。
4. M000_context：与3同参数，仅改A1B0C0；主CB来自4−3。

模型1与模型2的训练历史/骨干角色不同；不把差值当“DSM有因果增量”。模型3/4共享S1-0权重但前向策略不同，应按输出系统计case，实际共享计算只能在逐像素端点验证后使用。

绑定入口沿现有source_mechanism_plan与原N3/S1协议：

|对象|已绑定checkpoint SHA256|训练/角色|
|---|---|---|
|D25 P6 RGB-only|bef8dda6537b68fc51f300bc3789bbbef57682baedf92a3f7665217a4a2fde71|selected2000；records/research_d25_missingness_20261002T130253_1358078/jobs/P6/selected.pth|
|S1-0|5a8cd5c40576e1897fbb6a767dd2028016df402c2b3b6ae98994f55ac4cec58f|selected8000；research_post_n3_s1_20261007T083203_694293/jobs/S1-0/selected.pth|
|S1-3（后续复核）|c8b4d801da2a7a3937589aa3777885de810387a463009d4a8c6e23dc00d8d562|selected8000；同族S1-3/selected.pth|

以上是既有绑定引用，不是本轮重新散列服务器大文件。执行前解析loader/config/完整state、标记历史held4曝光、核对已存clean预测输入/窗口/精度/SHA，才可复用；不可从S1-0专家readout冒充仍是D25 P6原权重。旧总registry最后更新日期较早，不能作为当前实时队列；当前入口、带时间回报与真实原件优先。

第一轮范围固定Potsdam Val2 3_11/5_10，RGB local missing、25%、received RGB [0,1]输入置0后再走原专家归一化；DSM不损坏，known availability明确。沿现有native512/stride256、FP32+TF32和标签口径。生成器作用于完整tile，不能在每个crop重新随机。Test6/held4/final禁用；无训练seed扩展、DSM镜像、质量强度或故障检测训练。

## 4. 四类掩码与CPU可行性门禁

|家族|用途|GT参与|
|---|---|---|
|U-pixel|在合法图域内无放回选精确25%像素；CE参考|否|
|U-block-random|同固定primitive bank，合法位置均匀随机；CE块对照|否|
|S-grad|相同primitive bank，根据可用DSM梯度评分选择位置|否|
|U-block-matched|S-grad每组的受约束随机twin，匹配几何与类别构成|是；诊断限定|

每组在两tile分别由(protocol_version,tile,mask_realization_id,family/pair_role)导出随机流，随机发生器/版本须固定；训练seed42不改变。20个ID拟固定为001—020，不能按模型结果重抽。记录每个tile的实际不同mask数、两两重叠及有效随机自由度，不能把20个相同高梯度掩码当20次重复。

主primitive暂建议128像素。6000×6000的25%为9,000,000像素，不能由整数个128²块恰好组成。一个可行的固定模板是549个128×128加1个72×72，面积恰好9,000,000；全部block族和同ID的twin使用完全相同清单，不靠随机补像素或裁剪凑面积。两tile真实尺寸/有效输入域必须先核验；尺寸或有效域不符则重新制定生成协议，不能静默改变比例。此算术模板只通过面积检查，不代表真实mask生成器已验收。

建议候选位置使用固定可复现网格及每ID相位，primitive间至少8像素空隙，禁止重叠/截断，使连通块数量及各块周长一致；仍报告块间距和全图分布，不能据此声称整幅布局完全同构。候选库必须有足够位置容纳全部primitive；不以增加碎小块应付匹配失败。滑窗边缘距离/相位分层先固定，随机与结构组采用同规则。精确位置算法、匹配迭代上限与容差在CPU可行性阶段冻结，未经该阶段不得登记正式评价。

S-grad候选定义建议：读取与网络相同的可用DSM归一化输入；Sobel 3×3、reflect边界、g=sqrt(gx²+gy²)，无临时平滑；每tile有效DSM域q=90百分位，以g>threshold避免平坦区ties被全选。block分数取高梯度像素占比。用事先固定的随机偏置选块规则保留20组不同实现，不能每个seed取相同的确定性top-K。q=90和采样强度是候选设计值，不是数据验证结论；只可在读取模型结果前进行可行性核验并最终冻结，不看损伤分数调q。若没有可区分梯度或候选不足，标生成器门禁失败。

语义匹配在Full与NB有效域分别记录六类直方图、无效/边界比例和Car分母。建议先冻结NB六类比例最大绝对差≤1pp、Car差≤0.2pp、NB有效覆盖比例差≤1pp作为CPU可行性目标；匹配算法的尝试上限与不可行处理必须预设。匹配失败不是科学FAIL；不剔除失败seed后仍声称n=20，不在推理之后放宽容差。不能使用模型预测、loss或正确性参与匹配。若无法实现共同支持，保留未匹配总效应描述，主条件化PE记INCONCLUSIVE，不假装匹配完成。

S-boundary暂不进入Phase 1A。它依赖GT且NB指标排除了语义边界带；将来需要独立定义边界带与Full主诊断，并为它生成自己的matched twin，不能共享未匹配的U-block后宣称类别受控。DSM高梯度与语义边界相关，可记录boundary fraction作为描述；不无条件把它作为主匹配变量，否则可能移除本来想测的结构路径。

## 5. 指标与固定判定

对模型m、mask M，令V为NB有效标签域。C_clean_M与C_missing_M均在M∩V计数，对3_11/5_10先相加int64 6×6再算mIoU_fg5：

D_m(M)=100×[IoU_fg5(C_clean_M)−IoU_fg5(C_missing_M)]，单位pp。

clean必须是同一模型、同一前向协议、同一M支持的未损坏预测，不能统一拿另一基座clean来替代。每模型每tile clean只推理一次即可在不同M下复算；可验证后复用同源旧clean预测。缺失的fg5类/零IoU分母显式记录，不能用不同实际类别集合冒充固定fg5；不足以形成固定指标则主gate不可判。

对每个mask ID s先在两tile池化：

- CE_s=D(U-block-random_s)−D(U-pixel_s)。正负皆报告，不预设方向。
- PE_s=D(S-grad_s)−D(U-block-matched_s)。这才是建议的主位置效应。
- PE_total_s=D(S-grad_s)−D(U-block-random_s)，描述总体落点策略差。
- CB_theta(M)=Perf_theta,context(M)−Perf_theta,masked(M)，两输出在同一M∩V内比较。
- I_placement_s=CB(S-grad_s)−CB(U-block-matched_s)；I_geometry_s=CB(U-block-random_s)−CB(U-pixel_s)。整tile CB并列报告，不能与mask内CB混算。
- 建议另报[D_masked(M)−D_context(M)]以扣除可能的clean前向差；clean不同则不能把CB当纯损伤缓解。

主终点固定为S1-0的20个PE_s算术均值，另报中位数、完整分布、每tile均值、五类及no-Car。这里每seed内部先池化tile，seed间均值是对掩码随机实现的期望估计。跨seed再次把所有CM加总得到的指标是另一个非线性统计量，命名pooled-mask diagnostic，不能替代主终点、挑更好者报告。

建议事前开发判定：

|分类|条件|含义|
|---|---|---|
|STRUCTURED_SIGNAL|主均值PE≥0.30pp；两tile各自mean PE>0；no-Car均值PE≥0.15pp或至少4/5类平均damage差>0；匹配/计数完整|在该模型、两开发tile及生成机制下保留结构相关落点线索|
|INCONCLUSIVE / MIXED|0.15≤PE<0.30，或较大均值但tile/类别明显异质、匹配不可行、分母不足|不自动加到40、不寻找新q或换主模型；明确是哪种不确定性|
|NO_SUPPORT_THIS_PROTOCOL|PE<0.15且技术与匹配有效|本协议未支持追加结构落点研究；不证明所有空间失效不存在|

不采用“supporting inference没有明显反向证据”这种未操作化条款。固定其他模型作为并列稳健性报告，不能用其中最高者救主判定。CE/CB/I分别报告；Structured PE失败而CB成立时，保留一般上下文适应问题，不扩大为整个主线失败。CE/PE/CB均正也只是相容的受控证据链，不自动证明跨区域信息的因果中介或真实故障机制。

统计以mask pair ID为重采样单位，按ID同时保留两tile、全部模型与家族，报告条件于这两张图和固定模型的paired bootstrap区间。禁止像素/crop/primitive伪重复。sign-flip p值只有在明确对称性/可交换性假设后才作为敏感性；结构评分选块并不是两处理标签随机分配，不能默认称精确随机化检验。第一轮可不报告p值。

空间macro-block bootstrap非主必要项；若做，预先固定如1000×1000非重叠6×6网格，对全图推理后的计数重采样、同时保留两条件，不能把重叠512/256窗口当独立样本。不重跑裁剪图像，不把重采样CI当跨地域总体CI，也不据CI自动增加tile或seed。

## 6. harm/rescue、机制诊断与证据产物

先区分两个reference：同模型clean→missing的损伤转移，以及同一missing输入下base→candidate的方法救回/伤害；不能两者混用。

每种范围(M、not M、缓冲healthy、边缘带)保存reference correct总数/被改错数、reference wrong总数/救回数和逐类分母。若称“另一模态可救回”，分母必须限制为同条件DSM expert正确且reference错误，不能只统计所有错误像素。R0/DSM参考未执行时相应指标标未评估。matched输出支持外exact是构造保护，不当作独立学习到的鲁棒性证据。

保存mask canonical数组uint8{0,1}、shape、C-order、1=missing。canonical hash对明确dtype/shape/布局头加连续数组字节求SHA，另存.npy文件SHA，避免混淆.npy头与纯数组字节。PNG仅可视化；原数组可压缩无损归档，不将大型mask/prediction提交普通Git。metadata包括twin/ID、实际面积、primitive清单/位置、连通分量/周长/间距、window相位、gradient规则与分数、Full/NB类别/有效面积、boundary fraction、generator/protocol SHA及模型绑定。

known-answer检查必须覆盖：人工6×6矩阵与已知翻转数、same-support damage、健康区空分母NA、harm/rescue两套reference、tile→pooled、seed均值与跨seed pooled区别、no-Car重算、末端滑窗覆盖、mask全图复用、实际物理输入zero-fill、模型不读GT、C/M原端点与clean复现、20组/twin完整性。测试PASS前不执行新真实推理。本文没有生成器/测试结果，不填虚构PASS。

首批交付Table A协议/匹配质量、B空间形态damage、C主PE、D逐类/no-Car、E同权重CB交互、F伤害/救回/支持分母，并保留全部原计数。尺寸曲线留1C，未执行的G/H oracle表不得填估计值。

## 7. 如何接到F/H/R之后的新训练

先完整验收当前六组固定终点/轨迹/15对batch前缀/有效梯度、R0/保护/六E和DSM内容C/Z/S。CONTENT_PRE已完成只代表运行期技术完成，尚无原件对比回传；不预判DSM内容有用。

|Phase 0及新诊断结果|优先下一步|避免的误读|
|---|---|---|
|R16有独立增量且保护/R0底线通过|保留尾部适应；若PE/CB交互也支持，再冻结针对该子问题的最小方法对照|普通解冻本身不是新贡献；R−H还伴容量变化|
|H接近R，R−H不足|另行决定用更简单H作为后继候选；完整报告原R16判定|不能称后验H为原候选成功|
|F16追上R16|优先普通融合解码/预算解释；研究可观测支持策略的边界|停止增加分支深度来追分|
|PE弱而CB稳定|保留Context-Preserving Local Adaptation子问题，停止扩大结构mask矩阵|不强行写“结构性失效”创新|
|DSM内容诊断弱或混合|先设计同预算信息对照：完整DSM内容、固定无信息DSM、固定空间错位；同一参数容量/路由/损失|推理破坏有掉分不等于匹配训练证明互补；无掉分也不等于DSM无用|
|所有候选未越R0/保护底线|保留已知掩码R0作为强参考，先做失败空间分析与能力差距定位|不再无条件开新残差分支或路由族|

新训练只能选一个主要问题：若瓶颈是跨模态内容必要性，优先完整DSM/无信息/错位的匹配信息控制；若是结构分布转移，固定同一架构做random-block训练与structured-placement训练配对，唯一变化为训练掩码分布。若是新局部分支机制，至少有无分支、普通同容量局部适应、候选、无上下文同容量对照；训练初值/预算/损失/掩码严格同配。先用本轮结果简化架构，不把这些分支同时列为已授权训练矩阵，具体组数/步数留下一版冻结。

原输出支持外已是硬路由exact。在Y=base+M·residual的定义下，支持外输出不依赖分支参数，healthy区输出蒸馏为零或常数，不能宣称它学到了保护；要研究feature蒸馏或软路由必须另外定义并配对。zero-init残差也可能首步阻断更早层梯度，需按多步真实梯度检查。R0 teacher不是oracle，训练/推理双模型成本不能称免费；是否蒸馏由缺口与成本决定，不默认上teacher。

## 8. 本轮不采纳的扩张与后续边界

- S-boundary和64/128/256/512全部扫描不列首批必要项。20实现、4模型、2tile、3个额外尺寸、3种block家族可再增加1440缺失输出case；GT boundary另增至少160，且若另造matched twin会更多。先回答固定128主问题。
- GT mask内替换为真值只是“支持外固定且支持内允许任意正确预测”的指标上界；不能称整任务绝对上界。R0 composition是已知mask可实现强参考，不是oracle。若anchor已是R0，再拼R0没有新增证据。任何headroom必须写明同一受损输入、同一支持、同一参考模型与指标域。
- Router/MoE oracle ladder暂不做，也不重开已关闭D27等配方。标签oracle正余量不等于可观测特征能学习路由；best convex ensemble若在同一Val2选权重也有乐观选择。按patch accuracy选expert并不保证全局mIoU最大，细粒度oracle曲线也不自动是严格mIoU上界。真要研究须单独定义oracle目标、固定网格/边界和无泄漏校准划分。
- 外部Vaihingen不自动执行。先核查是否有合法未用于开发的split、兼容权重/类别/DSM处理与GSD。固定像素block尺寸在不同GSD代表不同物理尺度，必须事前选“像素尺度复核”或“物理尺度复核”，不能同时声称两者。q/规则固定、每tile无标签percentile计算可作为预定归一化，但不得用外部标签调q/模型。方向一致只能支持有限外推，不能替代独立来源设计。外部门禁仅约束外部检验，不阻止当前开发诊断。

## 9. 实施资源、登记与交接

Phase 0优先；即使一张卡在阶段屏障时短暂空闲，新诊断也不抢卡。用户release出的卡是供用户使用，不能自动拿来跑Phase 1。服务器由用户操作、无SSH；当前只能据18:54记录描述最后状态。未来新执行前查询旧队列/进程/锁/卡使用，禁止重复登记。新族独立目录须位于/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_structured_failure_v0_<time>_<pid>；本次不创建真实服务器目录。

640为模型输出×mask×tile计数，不是640次新训练，也未必等于640次完整独立forward。将原前测1252秒/24case机械摊销，640case约9.3卡时、均摊两卡约4.6小时，只作资源量级参照；模型/CPU统计/缓存/读取均不相同，不能当可靠ETA。真正排期需首个正式批次测量后更新，当前不拿GPU训练step速度估推理总时长。原F/H/R整队先前12–20h也只是粗估，并未获得R/完整评价耗时校准。

本轮交付只有设计评审、原附件留档和拟议矩阵清单。执行registry保持原运行信息；新设计另存planned manifest，registered=false、gpu_jobs_dispatched=0、optimizer_updates=0。下一实施任务再交付生成器、完整解析配置、known-answer测试、冻结mask registry、只读前序检查和可恢复推理控制器。未完成这些前置不称协议已执行或模型已通过。重要研究结论仍以完整原件验收为依据。
