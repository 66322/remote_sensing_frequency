# M2之后的证据边界与近期文献核对（2026-10-29）

- Origin：academic-research-suite / experiment planning；nature-academic-search / focused search + citation verification。
- Material Passport：v1.0；历史结果为ANALYZED_FROM_REPOSITORY，研究建议为UNVERIFIED；本文件未重新训练或复算全部服务器原始计数。
- GitHub证据基准：rebuild-v1-protocol-20260915 @ 68c97c979d4a638271ef50b4f5be8645dcafd35d。
- 范围：另读取用户原DOCX的摘要、贡献及相关方法段落（未逐表复核原稿实验），主要依据用户粘贴材料、D12–D27、Post-S1、Phase2.4、M1/M2及10月27日计划；近期相关研究为定向检索，不是穷尽性系统综述。
- 检索日期：2026-10-29。当前没有可用的学术数据库MCP，使用会议/作者论文、arXiv、作者代码与机构记录；未依赖二手文章的“必涨点/顶刊保证”。论文元数据、摘要和方法定位经过核对，不冒称所有论文全文逐表复现。
- 下一步：[分阶段实验计划](POST_M2_CAPABILITY_PRIOR_PLAN_20261029.md)、[准备表](../protocols/POST_M2_CAPABILITY_PREFLIGHT_20261029.md)。

## 1. 目前究竟支持什么

全部数值差为百分点pp；不同指标、分母、数据划分与模型预算不可混合排名。

| 证据 | 已有结果与正确含义 | 不能推出 |
|---|---|---|
| [D12结果](D12_RESULTS_20260924.md)及[协议](../protocols/D12_NIGHT_SEMANTIC_FREQUENCY_20260923.md) | 所谓语义主要是冻结特征的通道均值、绝对激活均值、局部对比度等压缩代理；未过实用收益和伤害检查 | 完整语义表征、对象上下文、文本常识均无效；旧融合特征也不等于纯DSM语义 |
| [D15](D15_RESULTS_20260926.md) | RGB-down4下，普通融合R05超过更强RGB控制+2.9585/+1.9245；有条件互补的直接线索 | 新方法还能在普通融合之上再涨同样幅度；真实云雾/传感器差异已经验证；应立即改做超分辨率 |
| [D18](D18_REPLICATION_RESULTS_20260928.md) | RGB+DSM相对更强RGB/灰度控制复合分数+1.0603/+0.9229 | 约1pp是信息论上限；DSM缺失鲁棒性成立；固定专家oracle是所有架构的上限 |
| [D21](D21_DETAIL_FREQUENCY_RESULTS_20260929.md) | 四个数据集×seed块，F2−M0为+0.160/+0.153/+0.177/+0.135；有小幅同向收益，未达预定实用门槛，并有缺失/局部伤害问题 | 频率完全无用；小幅整体提升即可证明新边界原理 |
| [D26](D26_COMPLETE_D27_FAILURE_REVIEW_20261003.md) | 选择端点XSF−B0为+0.156829；几乎不及普通联合适配J0；固定8k频率打乱差仅+0.073522；选择年龄存在差异 | 语义与频率的通用机制被证实；不同年龄的最高分可用于纯机制归因 |
| [D27](D27_FINAL_REVIEW_20261003.md) | 当前保护/补救损失使主分数下降约1.77–1.89；DSM-only-correct保持率+19.980085，RGB-only-correct保持率−4.240696 | 两者是不可突破的零和定律；约99.48%的路由集中可叫“全选DSM”（实际是双模态残差专家） |
| [Post-C蒸馏](POST_C_N1_RESULTS_20261005.md) | 正确掩码KL相对普通监督，剩RGB均值+0.041525、剩DSM−0.041961；普通监督解释主要改善 | 只换教师/温度即可形成新贡献；所有知识蒸馏都无效 |
| [Post-N2关系传播](POST_N2_E0_E1_E2_RESULTS_20261006.md) | 同容量空间控制86.636913，固定3×3双向关系86.629885，差−0.007028；高度/语义错配未形成有用差 | 此前没有测试几何关系；仅扩大窗口或系数就是新假设 |
| [Post-S1上下文](POST_S1_FULL_TRANSFER_PARTIAL_RESULTS_20261010.md) | P7−P6为+1.759726，P7−打乱P8为+1.952962，但P7仍比简单已知缺失掩码拼接R0低1.426292 | 从未考虑上下文；上下文已胜过强简单基线；已知掩码拼接具备未知故障检测能力 |
| [Phase2.4](PHASE_24_ACCEPTANCE_AND_ROUTE_REVIEW_20261015.md) | 零值比例stump解释了大量zero收益，复杂probe仍失败于保护要求；校准变好不自动带来分割增益 | 人工zero标记就是普适物理质量信息；一个uncertainty分数能自动可靠选路 |
| [M1](PHASE3_M1_ACCEPTANCE_AND_ROUTE_REVIEW_20261015.md) | DSM尺度/适配影响单模态，但补救跨seed变号、固定融合增量未成立 | DSM精度提升必然增加条件互补；tile中心化DSM是nDSM或真实离地高度 |
| [完整M2](PHASE3_M2_ACCEPTANCE_AND_CLOSEOUT_20261029.md) | 108训练、3,456,000更新、77,868评价；DF−D0主融合三seed均负，均值−0.001261；补救均值+0.276044但不胜多个控制；G1/G2/G4未过 | 所有互补问题失败；主融合“崩溃”；RGB抢占共享解码器梯度是本次唯一原因 |
| 同一M2的训练方式 | RGB教师固定，DSM按错误位置加权独立训练；不是RGB和DSM共同争抢一个可训练共享解码器 | 用M2直接证明联合训练模态竞争；用PCGrad必然修复M2 |
| M2存储/工程状态 | 第一次删除90端点，最后实际仍保留18；最终离线分析/大文件清理工具已发布，未收到执行回执；J工程失败，无科学结论 | 所有二次分析都完成、全部权重已删除、J假设失败，或可直接加载已退役的旧专家 |

D27中两类保持率分母分别为23,478,234与197,573,156；多救4,690,971与损失8,378,477个像素不能把百分比直接相抵，也不能据此建立不可避免的零和关系。GT分区只用于训练允许区域或事后诊断，不能输入部署选路器。

Post-S1的P结果是完整P支；同文T为阶段性结果，不把部分T结果冒称整个后续训练链最终验收。旧Val2被多次用于开发；M2外折同样已被查看。它们可指导下一步，不能重新命名为独立最终确认。

## 2. 对粘贴材料的关键修正

| 材料中的说法 | 核对结论 | 可保留的研究问题 |
|---|---|---|
| 静态融合触及“香农互信息物理天花板” | 不成立。没有估计条件互信息或证明Bayes风险；若干模型的小增益不能证明全局上限 | 强基线之后还剩什么条件信息、现有表示/决策是否能利用 |
| 梯度投影能锁死RGB正确区误伤为0 | 不成立。投影只约束当前聚合损失梯度的局部关系；有限步长、曲率、优化器状态、像素argmax及新样本都可能改变 | 先记录冲突与梯度范数，是否优于普通损失归一化/配重 |
| EDL的u=K/Σα能天然可靠识别全部退化 | 无此保证。它依赖模型/损失/校准，分布外可能仍自信；把该量直接等同绝对认知不确定性过强 | 在未见故障中能否比熵/温度校准更好预测实际错误，并提升同等风险下的任务表现 |
| 低秩旁路保证不遗忘、不误伤 | 不成立。低秩不限制更新范数，也不保证输出不变；即使主干冻结，适配器仍改变预测 | 在同容量/范数/训练预算下，适配方式是否减少可观测负迁移 |
| MIAM审稿人8分到10分证明遥感空白 | 未核到可定位的原评审引文；论文存在不等于这个引文存在，也不等于新任务必有创新 | 固定掩码已充分训练后，失衡驱动策略是否仍有额外价值 |
| D15已有2–3pp，所以幻觉恢复还会涨2–4pp | 混淆“融合相对RGB”的收益与“新方法相对强融合”的增量 | 清晰/大视野教师是否在学生无法判定处提供可学习目标，且超出普通蒸馏 |
| 三模块串联即可一两周达到顶刊 | 没有实验或审稿依据 | 每次只引入可检验变化，先证明核心关系，再讨论论文定位 |

数学边界：若对补救梯度投影得到g_r'·g_p=0，且用普通梯度下降，则保护损失的泰勒一阶项可以被约束；二阶项、随机梯度误差和多步演化不受该等式保证。损失变化也不等价于每个像素分类不变。建议将“零伤害保证”改为可测的clean/健康区/类别风险约束。

## 3. 近期文献与“已有到哪里”

下列链接用于方法定位与文献身份核验；不同任务原论文分数不直接作为本仓库基线分数。VERIFIED表示有可定位一手记录，不表示本项目已运行其代码。

| 来源 | 核验状态与范围 | 对选题的实际限制 |
|---|---|---|
| [DINOv3](https://arxiv.org/abs/2508.10104)，2025技术报告 | VERIFIED；稠密视觉特征与Gram anchoring等，模型系列可供迁移 | 当前DINOv2本来就是基础模型；仅换更大/更新骨干不是新机制。通用关系蒸馏也已有大量先例 |
| [SegEarth-OV](https://github.com/likyoo/SegEarth-OV)，CVPR2025 | VERIFIED作者代码/论文入口；RGB+文本开放词汇，处理空间分辨率与全局语义偏置 | 与监督RGB–DSM任务不同；training-free不能理解为组件从未训练，SimFeatUp本身有训练。文本全局信息也可能伤局部定位 |
| [RS5M/GeoRSCLIP](https://arxiv.org/abs/2306.11300)，2023初版 | VERIFIED论文；遥感图文预训练 | 可作文本区域探针来源，不等于已经具备精确像素分类或真实常识推理 |
| [DFormer](https://arxiv.org/abs/2309.09668)，ICLR2024 | VERIFIED论文 | RGBD预训练/模态适配已经存在，不能把为深度适配RGB特征当新问题本身 |
| [DFormerv2](https://arxiv.org/abs/2504.04701)，CVPR2025 | VERIFIED；材料隐含“2026新武器”应纠正；深度和空间关系直接作用注意力 | “DSM作为几何关系而非分类投票”已有近邻。需要说明航拍DSM高程、地形、GSD、错配及对象关系的实质不同 |
| [BATFNet](https://www.mdpi.com/1424-8220/26/10/3205)，Sensors2026 | VERIFIED出版社检索记录与摘要；DSM边缘引导双向融合与解码细化，原稿已引 | 即使不用基础模型，DSM边界先验也有直接RGB–DSM近邻，不能只与室内RGBD方法比较 |
| [DLGCNet](https://air.unimi.it/handle/2434/1249949)，2026 | VERIFIED机构/出版社检索记录；视觉基础模型低秩适配与图卷积融合，原稿已引 | 基础模型适配加跨模态图关系已有直接近邻，正式投稿时需统一协议比较 |
| [SAM辅助对象/边界约束](https://hub.hku.hk/handle/10722/366291)，TGRS2024，DOI 10.1109/TGRS.2024.3443420 | VERIFIED机构记录及摘要 | 加SAM区域一致性或边界损失本身已有直接遥感先例 |
| [RS-SAM](https://openaccess.thecvf.com/content/ACCV2024/html/Zhang_RS-SAM_Integrating_Multi-Scale_Information_for_Enhanced_Remote_Sensing_Image_Segmentation_ACCV_2024_paper.html)，ACCV2024 | VERIFIED会议记录 | SAM多尺度适配是基线来源，不是无人做的路线 |
| [CrossEarth-Gate](https://arxiv.org/abs/2511.20302)，[作者代码](https://github.com/ShileiCao/CrossEarth-Gate)，CVPR2026 | VERIFIED论文/作者录用记录；空间、语义、频率PEFT模块与Fisher选择 | “语义+频率+动态门控”不能仅靠组合名称建立新颖性；其跨域设定与本仓库同城开发也不同 |
| [MIAM](https://proceedings.iclr.cc/paper_files/paper/2026/hash/29536cd0e09e7f27d9eaaed7330f96cb-Abstract-Conference.html)，ICLR2026 | VERIFIED；生态多模态GeoPlant/TaxaBench，失衡感知动态掩码 | 不是已在稠密RGB–DSM分割验证的收益；要对比同掩码预算的固定策略，不能只对比无增强模型 |
| [DIS2](https://openaccess.thecvf.com/content/WACV2026W/CV4EO/html/Kieu_DIS2_Disentanglement_Meets_Distillation_with_Classwise_Attention_for_Robust_Remote_WACVW_2026_paper.html)，WACV2026 Workshops / CV4EO | VERIFIED会议记录；应明确是Workshop，非主会 | 缺失模态补偿、解耦、蒸馏与类别注意力已有前作 |
| [CMH-CL](https://github.com/TINYWAI/CMH-CL)，[IEEE论文入口](https://ieeexplore.ieee.org/document/11271136)，JSTARS | VERIFIED作者来源；光学–SAR缺失模态建筑足迹提取 | 不能忽略SAR/DSM差别、二分类/多类差别而直接承诺迁移效果 |
| [MSSDF](https://github.com/CVEO/MSSDF)，[作者出版记录](https://www.whu-cveo.com/research/)，Information Fusion 2026 | VERIFIED作者记录；模态共享自监督蒸馏 | 进一步说明通用跨模态蒸馏并非空白；具体预训练覆盖、权重可用性需执行前核验 |
| [STARS](https://arxiv.org/abs/2601.17342)，[作者出版记录](https://www.whu-cveo.com/research/) | VERIFIED；作者页面列International Journal of Applied Earth Observation and Geoinformation 2026，材料列Information Fusion不符 | 共享/特有表示、双向翻译和语义对齐是近邻；不能把缺失模态恢复本身当新颖性 |
| [PCGrad](https://arxiv.org/abs/2001.06782)，NeurIPS2020 | VERIFIED；梯度手术早已存在 | 只作为优化对照或方法来源，不宣称首次梯度投影，也不继承不存在的逐像素零伤害保证 |
| [EDL理论边界](https://arxiv.org/abs/2402.09056)，ICML2024 | VERIFIED；讨论可识别性、收敛和不确定性解释 | 支持谨慎检验EDL，不意味着所有EDL方法无效 |
| [SENSSE](https://pubmed.ncbi.nlm.nih.gov/42879268/)，DOI 10.1109/JBHI.2026.3744206，2026在线 | VERIFIED检索记录；医疗合成与分割 | 不是遥感故障自动切换的证据；本次页面部分抓取受限，不从中推导未读的遥感结论 |
| [MTPOA](https://mail.svedbergopen.com/index.php/ijaiml/article/view/299)，2026，DOI 10.51483/IJAIML.6.2s.2026.134-141 | VERIFIED出版入口；不是新近才出现的梯度投影原理 | 优先以PCGrad原论文说明原理，不把年份新等同方法先进或必定适用 |
| “MLDANet / MDI / DALoRA”指定组合 | UNRESOLVED；未定位到对应遥感论文，近名结果不足以确认 | 不作为设计前提；有准确标题/DOI后再核对，不断言其虚构 |
| “2026年8–9月混沌冲突Dempster–Shafer融合” | UNRESOLVED；缺作者/标题/标识 | 不引用为前沿证据，不因术语复杂而上调优先级 |

## 4. 哪些方向收益容易递减，哪些仍可做

判断是基于上述近邻与本仓库结果的研究建议，不是全领域终结论：

- 竞争密集、当前不宜单独主打：清晰配准小基准上再加注意力/频率模块；一般缺失模态蒸馏；SAM掩码辅助损失；通用LoRA或更换DINO；用单一校准指标论证可靠融合。
- 仍值得实证：外部视觉先验是否提供条件增量；地形高程和对象结构之间的关系何时可信；先验错配时是否能少犯错误；同成本下可否把清晰/广视野能力迁移给受限输入；独立地区真实输入差异下是否成立。
- 需要改变证据而非加模块：同一Val2反复调参不能支撑新泛化结论；人工down4不能独自证明真实云影或低质DSM；已知缺失mask不能替代未知故障检测。
- 独立路线仍有价值：[连续地图维护](NEXT_STAGE_DECISION_EXPERIMENTS_20261027.md)回答时间维度的错误恢复。它是换问题的候选，不能因为原线某配方失败就直接宣布为新主线。

对原稿已读摘要/贡献段落，方法仍以协同增强、分层交互、频率解码的组织为主；这与编辑认为组合已有策略的意见相符。原稿自己已引用BATFNet和DLGCNet，更不能以“几何先验”或“大模型融合”这两个宽泛词作为新增贡献。该判断不是原稿全部公式/结果复核。

对原稿，文字重写可修正主张，却不能补出独特机制。若要回应The Visual Computer的拒稿理由，应先建立“可定义的几何—结构关系、与近邻的差别、正确/错误先验反事实、局部边界与损伤证据”，再重写方法和实验；若仅获得一般涨点，应据实际贡献调整定位，不能用大模型名称包装成新原理。
