# Phase 2：匹配专家、静态吸收与可观测互补（2026-10-13）

状态：DESIGN_SPECIFIED / EXECUTION_NOT_IMPLEMENTED_NOT_REGISTERED。本文件替代同日PAIRED_RELIABILITY_FEASIBILITY草案的排程，属于本次用户请求下的下一阶段设计，不代表服务器已经开始训练。用户授权规划GPU0/1、至少一天可用窗口、超过一天继续，并要求内存驻留与并行分析；服务器仍由用户执行，无SSH。本轮不增加训练seed，不访问Test6/held4/final，不自动重试失败配方。

## 1. 单一研究问题与修订依据

问题：控制骨干、初始化、数据流和训练预算后，RGB与DSM还保留多少条件互补；强静态融合吸收多少；剩余差距是否具有部署时可观测、跨两张开发影像一致的结构？

已验证线索：S1的DSM对应内容干预损伤大幅上升；五专家oracle相对最佳固定R16约10.11pp，但专家架构/训练历史混杂；简单分箱偏好尚不稳定；ECI约1.0205，不支持强边界集中。详细来源见[Phase1.5结果](../experiments/PHASE_1_5_RESULTS_20261013.md)。

采纳用户所附审查：DSM-only的RGB缺失damage恒为0，不用它与S1约21pp比较来证明fallback；保留2×16k；DSM固定复制3通道；专家先训练后冻结；双向镜像面板；C与L分门禁；动态头比较匹配静态基线；禁止非共位置特征替换但允许共位置空间权重。未采纳：自动增加learned DSM adapter/frozen-DINO第三专家、失败后自动转residual旁支、用21→15作为新系统硬门槛、把现有证据写成多训练seed验证或方法学新颖性。

本次进一步修正两点。第一，内部身份检验已有720份真实回执，不再新跑。第二，硬availability回退使已知单模态缺失ROI只有一个合法专家，动态路由在该区域没有自由度。故区分reported missing面板（连续性/保护）与unreported corruption面板（动态可靠性主检验）；不能用已知mask机械选另一专家就声称学会可靠性。

## 2. 阶段安排与训练数量

| 阶段 | 实验 | 更新预算 | 后继依赖 |
|---|---|---:|---|
| 2.0 | 旧证据内部DSM身份、类别/专家/ROI分解、finding登记 | 0 | 身份回执本次已审计，其余CPU复用原计数 |
| 2.1 | A_RGB、A_DSM匹配单模态专家 | 2×16000 | 配对流、来源、梯度和评价技术检查通过 |
| 2.2 | 8k轨迹诊断、16k双向missing/corruption、two-expert oracle、C/L | 0 | 固定16k专家作为头阶段输入 |
| 2.3-0 | B0静态校准混合、B2同容量信号消融 | 2×8000 | 专家冻结；不与专家joint train |
| 2.3-1 | 静态后剩余差距与保护审查 | 0 | C、L、剩余差距和静态保护全部通过 |
| 2.3-A | B1动态可靠性、B3 DSM统计错位控制 | 条件性2×8000 | 全部结果汇总后停止，人工科研复核 |
| 2.3-B | capability-preserving residual | 不登记 | 仅作为失败原因明确后的独立备选设计 |

固定核心4训练/48000更新；条件性追加2训练/16000更新；最多6训练/64000更新。2.0—2.3-0中独立CPU分析与GPU工作并行；B1/B3有科学依赖，不能为填满GPU越过门禁。门禁失败只写STOP/INCONCLUSIVE，不调阈值、不换bin、不追加seed或自动转旁支。此文件没有enqueue脚本、运行ID或PID。

## 3. Phase 2.0：复用既有证据

2.0-A已完成轻量回执审计：720个S1非clean案例，intact240/crop_shuffle160/tile_shuffle160/zero160；25%为640，5%和10%各40，两tile。所有案例reused_old_prediction=False，own_logit_identity.dsm_only=True。实际infer_one对每个窗口的 dm & ~rm 像素使用torch.equal比较最终logits与parts['dsm']，不相等立即报错；N1.forward在该支持域显式选择dlog。缺失区域非空；本轮rgb_only标志可能来自空支持，不能据此声称双向身份已验证。

因此已具有“当前S1执行图在RGB缺失处精确回退到自身DSM logits”的运行回执证据，强于仅共同M5曲线不变；不是独立重跑GPU或另存完整双份logits。使用相同窗口与拼接规则时，缺失位置prediction agreement=1、逐类预测一致和同域ROI指标相等是该恒等式的推论；KL=0是相同有限logits下的数学推论，不能伪装成另做一次KL测量。DSM分支与旧D15不是同checkpoint，21pp不是DSM能力上限。

[身份审计回执](../../records/phase2_design_20261013/internal_dsm_identity_audit.json)。2.0-B从已存6×32 joint-correct、系统CM和类别计数分解class×mask×expert；2.0-C复用B的5/10/25%原CM比较missing/healthy/full NB/commonM5。只在已有字段支持时复算；缺字段标记不可恢复，不悄悄重推全量。2.0-D登记[F-DSM-ALIGNMENT-DEPENDENCE等发现](../experiments/FINDINGS_REGISTRY_PHASE2_20261013.md)。

## 4. Phase 2.1：公共训练契约

数据只用Potsdam fit12：2_12、2_10、7_8、3_12、5_12、7_9、6_9、7_7、4_12、6_8、6_12、6_7；Val2=3_11、5_10。公共DINOv2-vits14，仓库external/dinov2_7764ea0、上游commit7764ea0f912e53c92e82eb78a2a1631e92725fc8；公共预训练pretrained_external/dinov2_vits14_pretrain.pth，启动前校验既有来源及SHA，写入manifest。不得加载旧分割checkpoint。

执行图采用现有D24Segmenter(optical_only=True,last4=True,prototype=False)等价独立包装：RGB投影384→128（1×1+GN8+GELU），decoder128→128（3×3+GN8+GELU）→6（1×1），输出最近邻回512；没有aux/detail/prototype模块。两专家共享逐字节相同encoder预训练状态和seed42生成的同一投影/decoder初始化。

训练参数：encoder.blocks[8:12]全部参数 + rgb投影 + decoder全部参数（含分类层）；encoder其余参数及最终norm冻结。两模型参数名/形状/数量完全一致，启动清单给出精确数值及state SHA；继承encoder.eval以关闭随机dropout，但开放尾4块梯度，不能误包进no_grad。初次反传验证允许参数连接、冻结参数无梯度、非零更新覆盖；不通过即技术HOLD。

RGB=float32原值/255。DSM使用原loader全tile minmax：(d-min)/(max-min)，有限且非恒定，原min/max在未施加任何损坏前保存，缺失/噪声后不重新归一化；复制[D,D,D]。两模态都进入同一ImageNet mean=[.485,.456,.406]、std=[.229,.224,.225]通道变换；此项不同于旧D15的“不做ImageNet归一化”，必须明记。DSM复制后经三通道不同mean/std不会仍是相同数值，但执行图、参数与预训练完全匹配。此为控制基线，不宣称对DSM最优。

共同训练16k、physical batch16、无梯度累积、512×512、seed42；clean单模态CE六类等权，ignore255，不添加恢复/蒸馏/一致性损失。tile均匀抽样、合法坐标均匀裁剪，同步水平/垂直翻转各0.5；无旋转/尺度/颜色增强。key=(42,phase21,step,sample_index)确定所有crop/增强，模态分支不得消费额外共享RNG。每步保存batch_hash（规范化crop清单+label字节摘要），RGB/DSM输入分别保存hash，不能要求不同模态输入字节相等。wall-clock同步无要求，数据步号一致即可。

AdamW：encoder尾4块lr=2e-5，投影/decoder lr=2e-4，betas=(.9,.999)，weight_decay=.01，eps=1e-8；所有允许参数遵循相同规则。前100步系数0.1+0.9*s/100，之后(16000-s)/15900线性到0；bf16 autocast、FP32 loss/master weights，TF32设置同旧包，梯度范数仅检查有限不裁剪。每500步保存可恢复状态（optimizer/RNG/step/stream hash），永久保留4k/8k/12k/16k。技术smoke从临时同初值运行后丢弃，正式重新加载公共初值，不计入训练预算。

4k/8k/12k/16k进行Val2 clean评价，记录Full/NB fg5及6类；clean Full fg5最大、并列较早作为secondary selected。Phase2主比较及下游固定使用16k端点，不因Val2结果挑8k或各专家不同age。8k来自同一16k学习率轨迹，不是独立8k日程的预算因果比较。无论8k看似平台还是仍上升都完成16k；若16k仍明显上升则如实注明未证明训练充分，不自动延长。

## 5. Phase 2.2：双向面板与不同支持域

复用既有四族pixel/random/gradient/matched、20个realization、两tile、25%精确mask SHA。镜像DSM使用同一空间mask，不另按DSM梯度生成一套mask，避免改变比较对象；matched含GT匹配信息只作诊断，模型不能读取族/ID/GT。

P-M：reported RGB missing与reported DSM missing，2方向×4族×20×2tile=320物理场景；缺失模态归一化后置零，availability如实报告。所有候选在单可用模态位置强制原专家logits回退，双缺失排除有效支持且另报coverage。分别报告full NB、missing ROI、healthy ROI（沿原固定定义）、common支持；不能期待B1在单可用ROI比B0更好。

P-U：上述每个空间mask施加两种未报告局部破坏：归一化后置零、down4后覆盖mask；availability均保持True。共640场景。down4完全复用既有area下采样/上采样算子的定义，执行包逐项锁定库与参数。物理零和P-M完全相同，仅报告标志不同；必须配对保存，不能给路由暗传mask或condition。P-U分别报告RGB/DSM故障与两种破坏，不能只看最有利分支。

固定16k完整P-M/P-U；8k仅P-M和clean作预算轨迹，P-U不额外跑8k。Secondary：5/10% pixel嵌套missing（两方向×2比例×20×2tile=160）、全模态缺失两条件、原协议22普通条件（重叠只算一次）。主门禁只用注册P-U，P-M为连续性及保护。主分数=每realization先池化两tile CM计算NB fg5，再对4族、2方向、2破坏等权；Full/fg6、逐类、missing/healthy ROI和每tile独立保留。

不改变旧Phase1.5指标；旧五专家与新二专家池不同，初始化/骨干/训练均变化。新oracle变小不能定量归因成“消除训练混杂解释了旧10.11pp的多少”，专家池数量和组成同样改变；只报告两个体系的描述性差别。

## 6. Oracle定义、Gate C、Gate L

oracle采用两个专家原argmax：RGB正确选RGB，否则DSM正确选DSM，否则按RGB预测；DSM优先作为固定敏感性诊断，不挑更高版本。硬oracle正确覆盖率、各自unique-correct和both-wrong及int64 6×6 CM都保存。P-M额外计算受availability约束的oracle，单可用ROI上它等于合法专家；不把不合法专家输出计作可部署空间。

H_initial=M_hard_oracle-max(M_RGB,M_DSM)；best为整个注册面板的固定专家，禁止逐像素/逐条件选best后当固定参照。分方向同样明记各自best定义。该mIoU差是诊断差值，不是数学上界；soft/logit融合可改变错误类别甚至超过此硬oracle。出现负差照实报告，不裁剪，也不以负分母计算“吸收率”。

C：在P-U的两方向各自宏平均H_initial≥2.0pp，且两tile对应方向H_initial均>0。阈值是本轮预算分流规则，不是文献定律；弱/单向/低支持均保留结果，不宣称双向成立。

L不再事后搜索“任意70% bin”。Primary observable仅用两专家归一化熵差z=H_RGB−H_DSM，计算定义由实际可部署输入链冻结。固定两尾：z≤−0.25选RGB，z≥0.25选DSM；中间不作偏好声明。两tile每个尾部在整个P-U各至少10000个不同空间坐标、每方向至少10/20个mask各有256个分歧像素；重复mask像素不当独立样本。

仅在A≠B、GT∈0..4的支持上统计W_A=P(A正确且B错误|该尾部,分歧)，并保留双方都错，不能只对“一方正确”归一化造成70%虚高。RGB尾W_RGB≥.70、DSM尾W_DSM≥.70须两tile各自满足；并在每个故障方向，预定熵规则相对同支持的最佳固定专家正确率增益≥2.0pp、两tile均正。无GT class、mask family或故障ID进入规则。其余margin/DSM统计分箱只作secondary，不能替换primary救门禁。

该L只判定这一预注册信号规则是否足以支持当前小头预算，失败不等于所有多变量学习不可能；低支持记INCONCLUSIVE。20mask配对bootstrap5000次仅作开发扰动区间，tile只有2，不能写独立泛化或多训练seed显著性。

## 7. Phase 2.3：先强静态，再条件动态

两个专家16k端点冻结，只训练输出混合头，共享新的phase23 batch stream。B0/B2先执行，各8k；不因C/L未过而省去静态基线，因为“静态能否吸收空间”本身是主问题。动态B1/B3须完成静态后再决定。

所有头输出共位置逐类混合logits：z_c=w_c*l_RGB,c/T_RGB+(1-w_c)*l_DSM,c/T_DSM。温度初始化1并限定[.25,4]，权重初始0.5；只在两模态reported available处混合，单可用处不温度缩放、直接原专家logits。归一化/拼接/availability覆盖位置、window与输出分辨率对所有臂完全一致，在执行包技术测试中锁定。

B0：6个逐类常数混合权重+2个温度，强于简单0.5概率平均。
B2：与B1同参数量12→32→6的逐点GELU MLP，前10个可靠性输入置0，只保留2个reported availability；同样2个温度。
B1：同MLP，12输入为两熵、两margin、概率L1差、argmax分歧、RGB局部std、DSM局部mean/std/gradient、两个availability。局部统计窗口固定5×5、输入[0,1]、边界replicate，有效区域归一化、无支持填0；熵除log6、margin=top1−top2。DSM梯度使用固定有限差分，不能事后换特征或窗口。
B3：与B1同初始化/容量/数据，将DSM mean/std/gradient三张统计图固定滚动半幅；只破坏可靠性统计对应，专家输入、专家logits、availability与GT保持原坐标。这是负控制，不能部署，不能把它等同DSM内容shuffle。

B0参数量少于B1，需要B2容量控制。B2与B0可能函数近似等价，仍完整报告，不能当两个独立重复。所有MLP最后层零初始化、相同其他参数初始化；8k AdamW lr2e-4、wd.01、betas(.9,.999)、eps1e-8、100步warmup及8k线性衰减；batch16、相同seed42/公共流、仅六类CE，专家全冻结并eval。固定8k主比较，4k/8k保存，不按结果延长。

训练取fit12的独立掩膜随机流，不使用Val2 mask/GT-matched生成器。16个sample的一个batch配额：clean2、reported局部RGB/DSM missing各2、unreported局部RGB/DSM zero各2、unreported局部RGB/DSM down4各2、全RGB/DSM missing各1；合计16。局部25%，pixel和64×64随机块按step奇偶切换。每臂完全同crop/label/geometry/treatment/mask，顺序由确定性键打乱。训练不含GT引导gradient/matched，以保留其评估意义；双缺失区域不纳入此轮训练，固定诊断coverage另报。

M_static=max(M_B0,M_B2)在同一完整面板选择一个全局静态参照；报告两者，不逐条件取最大充当一个系统。H_residual=M_hard_oracle−M_static；报告signed gap与B1相对B0/B2的直接差，吸收比例仅H_initial>0时描述，不称理论恢复率。

动态入场：C和L均通过，H_residual在P-U两方向均≥1.0pp，B0/B2较好者clean相对零训练0.5混合下降不超过0.3pp，P-M单可用ROI回退identity通过。否则不派B1/B3。两张反复使用的Val2门禁只是开发阶段分流，不是独立验证。

动态接受：B1−B0及B1−B2在P-U主均值均≥0.5pp；每方向均≥0.3pp且两tile同方向增益>0；clean及healthy ROI相对同一个全局静态参照均≥−0.3pp，最差条件差≥−0.5pp，P-M单可用ROI exact保护。B1−B3若<0.3pp或两tile异号，只能支持一般条件建模，不能声称DSM空间统计机制。以上阈值为预先预算/保留规则，不用旧21→15替代。

## 8. GPU/CPU/内存与24–48小时窗口

用户最新free -h：total1.9Ti/used4.2Gi/free1.8Ti/available1.9Ti/swap0，粘贴未带命令时间。足以支持大内存规划，但启动需读取进程affinity、CPU quota、cgroup memory.max/current、MemAvailable、GPU0/1显存及其他占用。不能由Git压缩176线程或主机总内存推断容器配额。只读资源清单是执行包前置，不需用户逐项手抄。

排程：
- 准备：CPU并行校验/读入fit12与Val2、2.0旧证据分解，GPU0/1同时做各自短技术smoke；两卡可并行，避免旧串行smoke长等待。
- A_RGB在GPU0，A_DSM在GPU1，各自训练到16k；只要求step数据一致，不设每步或4k全局屏障。先完成的一卡先做自己的待评估/缓存，等待科学配对不等于停止独立工作。
- 两卡共享2.2推理/cache任务，缓存未损坏模态预测；同一clean DSM不因20个RGB mask重复前向。每tile/case完成立即交CPU做CM/分箱，不等GPU队列整体结束才分析。
- B0 GPU0/B2 GPU1，共用冻结专家缓存；C/L分析同时在CPU做。通过静态后门禁才B1 GPU0/B3 GPU1。CPU统计、压缩和上传准备与GPU流水重叠；单卡同时只一个重GPU worker，CPU队列不得独占全部可用核。
- 计算结束即停止并输出摘要，不以低GPU利用率认定未运行，也不为补足一天自动加无关任务。

预留首日24小时并可延长到48小时及之后，无24h强停。规划量级：准备/校验0.5–2h；匹配训练及轨迹评价6–14h；双向推理/缓存/静态4–12h；条件动态及末轮评价3–10h，可重叠。新图未实测，总墙钟可能短于或长于一天，这不是承诺最低运行24h或按时结束。正式前200步及前8个完整case分别校准train/eval/CPU吞吐，给含评价与尾部统计的ETA。

内存：fit12+Val2一次校验、解码、归一化后只读驻留，标签uint8按batch转long；两个训练worker可共享只读mmap并warm page cache，避免复制大数组经IPC。训练tile实际工作集先nbytes统计；不预生成16k完整RGB图像batch。

冻结头阶段缓存公共8000步batch的两专家低分辨率FP32 logits/必要统计。按16×6×128×128×4×2×8000估算，仅低分辨率双专家logits约93.75GiB；缓存全512 logits约1.46TiB，应避免。只有证实最近邻重建与原实际执行链逐值等价才使用该紧凑缓存，不能改变网络输出分辨率。标签、mask、统计另计，采用分块hot set与非压缩可mmap的cold存储；训练和Val缓存分开、绑定model/input/stream/precision SHA。未压缩常驻副本避免每case重复解压，磁盘原件保持完整。

运行初始hot-cache预算256GiB；有效预算=min(配置预算,实际可用内存50%)，若估算超过则调度分块，不能OOM后暗改batch。fit12/Val tile、双卡pinned预取、CPU临时数组另列预算。具备余量且实测page fault/IO瓶颈时可在预声明≤50%范围升至512GiB，不改科学数据和数值。无需占满1.9TiB。

CPU分析首选16个case进程，参数=min(16,max(1,floor((有效核数−预留核)/2)))，每进程数值库1线程；GPU训练期间为每卡crop loader预留8线程和管理核。实际有效核足够时允许校准8/16/32并发，选择每秒case更高且内存/IO稳定的一档，所有校准case只算一次、保存输出hash。它们是工程并发档，不是新科学实验。避免32进程各自再开32个BLAS线程。crop loader先每卡8线程、prefetch8 batch、pin_memory，空等待占比>10%再在预算内试16线程/prefetch16，顺序/hash必须相同。

验证microbatch主协议仍8以保持旧比较，预取准备可加快；若改16/32，必须先锁定新配置并验证标签/CM和浮点容差，不能中途静默改变。大显存不等于单进程利用率自然高；指标记录data_wait、H2D、forward/backward、stitch、CPU分析、压缩/写盘、队列积压、RSS/显存、GPU idle原因，60秒心跳。区分“依赖未就绪”“数据等待”“CPU统计”“真正失败”。

## 9. 执行包与证据交付

源码与配置另建执行包，不修改旧immutable快照。所有记录位于/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/对应新实验目录；本规划尚未生成目录。明确检查原队列完成、旧进程/锁退出后才能唯一登记；已完成队列不重复enqueue。资源探针、技术smoke、固定科学门禁、断点与HOLD写回各自回执。

上传仅manifest、summary、完整int64 CM/逐类/分层计数、batch/parameter/checkpoint/input绑定、必需日志和故障/完成回执；逐case计数批量JSONL无损打包并保留内部索引，源码引用固定commit与执行差异。数组/权重/完整性能日志保留服务器索引。上传幂等、失败重试既有worktree，同一run不能每次生成重复完整evidence。

下一步是实现该设计并完成CPU及真实双卡技术核验，再发一次性启动命令。当前仅完成设计、源码审查和旧回执补充审计，没有在本地或服务器启动GPU训练。新方法贡献、双向改善、多seed/独立泛化均待后续证据，不写成当前已成立。
