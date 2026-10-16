# Post-S1缺失支持×参数隔离：GPU0单卡冻结执行协议

## Material Passport
- Origin Skill: academic-research-suite / experiment-agent（run，内联执行包开发）
- Origin Date: 2026-10-08
- Version Label: post_s1_support_gpu0_execution_v1
- Verification Status: CPU_CHECKED（合成数据/专家/进程；真实服务器权重、Torch2.2.2+cu121和GPU科学结果待回报）
- 用户已明确授权按[规划](POST_S1_SUPPORT_GPU0_PLAN_20261008.md)实施，本轮唯一物理设备GPU0。
- 发布态READY_NOT_REGISTERED：助手完成代码/CPU检查，服务器仍由用户终端启动，无SSH。
- 研究问题、路线角色、全部门槛保持规划；新增代码并不等于方法成立。

## 1. 先前事实与新族边界
前置[九组结果](../experiments/POST_N3_S1_RESULTS_20261008.md)已验收。原执行0e22438a7131a0a1f28098e675c3367d40236398，原件38d205591abe00179bebfb36a17595d4d7b75f47，结果验收4163107e55bc560a8ba83784e3759caa3a4a299b。N3当前区域配方停止；S1 RGB局部U +4.102047pp但最差primary tile −0.391546pp，旧gate=False。新族不救旧gate、不改论文主线：仍为RGB–DSM条件互补与退化/缺失分割的可行性探索，恢复旁支；新研究族优先RGB局部问题。

最后服务器查询2026-10-08T22:11:10.555448+08:00，原queue最后观测06:37:48.607436，N3_S1_COMPLETE_AWAITING_REVIEW，九组COMPLETE/8000，查询时controller/worker LIVE=False。不是本次实时查询。登记/控制器均再核原queue、绑定、锁及worker存活，不重复启动。

## 2. 统一科学契约与十组
P0—P9全部从旧S1-0 selected8000完整state初始化（SHA256 5a8cd5c40576e1897fbb6a767dd2028016df402c2b3b6ae98994f55ac4cec58f），fresh AdamW/new8000/seed42/physical batch16、原paired clean/aug crop、augmentation与CE。expert anchors、split、input manifest、DINO repo与base config继承已冻结绑定。Potsdam fit12/Val2=3_11、5_10，native512/stride256，NoBoundary fg5主/Full及6类诊断。held4、Test6、独立final不得加载。

A共享原last4/heads与新残差头更新，或冻结全部F0参数及统计，仅训练新头；B原特征支持B1，或旁路保留上下文B0；C全域G，或仅RGB缺失且DSM有效位置L。P0/P1=共享G B1/B0；P2/P3=共享L B1/B0；P4/P5=冻结G B1/B0；P6/P7=冻结L B1/B0。P7为固定主候选。P8=P7支持分层空间打乱；P9=P7仅logit/mask校准控制。

实际头264→64（1×1）→GELU→6（3×3），20422参数，最后层全零初始化。同专家前向取晚期特征；B0额外执行轻量pyramid，不重跑编码器，原F0 masked graph不变。输出delta上采样后用native mask写入；full-window RGB或DSM全缺失仍F0。冻结L非支持位置的精确保护是工程构造属性，不能单独作为创新。

P8固定seed42，以availability在特征网格形成两分层，各分层循环置换offset=1+42%(n−1)，同时打乱可用与缺失位置的上下文，不跨支持层、不移动输入/DSM/GT/base logits。分层单token恒等，实际moved/total token记录。P9将前256特征槽置零，保留原logit6＋mask2；容量相同但部分参数没有有效暴露，单列。总参数/可训练量、训练时间/峰值、残差头MACs与E实测推理时间均记录，不宣称全模型FLOPs已测。

损失严格继承每view .5 fusion CE＋.125 RGB own CE＋.125 DSM own CE；clean/aug各一完整batch，同一更新。新增support_objective只补两view分母/暴露记录，CPU与旧objective逐值等价。无目标缺失batch允许零梯度，记录8000统一优化器步与实际branch_exposed/nonzero更新，不重采样。

## 3. 阶段与设备约束
D0（CPU准备，无更新）→D1（GPU0，零训练）→P6,P7,P8,P9,P4,P5,P2,P3,P0,P1→E（GPU0，零训练）→独立汇总→SUPPORT_COMPLETE_AWAITING_REVIEW。单worker串行，前一GPU进程退出并验收complete绑定后才启动下一项。全部GPU脚本仅接受--gpu 0，CUDA_VISIBLE_DEVICES=0；控制器只查询物理0的UUID/竞争PID，无资源审计。GPU1不能被派发或作为空闲回退。

CPU检查/准备与汇总隐藏CUDA设备，GPU0等待竞争进程释放；不杀其他任务。每GPU任务24h正有限工程超时，CPU阶段12h；无科学总截止。硬超时先通知日志后终止自有worker，超时即使returncode0仍TIMEOUT。故障/验收失败停止后续派发，保留记录，不自动重试/加seed/新族。controller异常保留detached worker，先查再显式接管，不重启整队。

## 4. D0与D1
D0只读旧S1-0/1/2/3绑定预测，按missing内外、missing edge16、label boundary4/interior记录rescue/harm、两者均对/均错、逐类分母和CM。重叠区域与互斥优先“label edge→missing edge→inside→other”单列。普通条件上的空间位置以冻结U掩码作为同位置诊断参照，并非声称完整输入发生物理缺失。mIoU由CM重算，不能用净救回像素替代。

R0使用已知RGB局部missing、DSM有效且存在RGB观测窗口的mask选择S1-3，否则S1-0，不使用GT或oracle路由。两个已有完整模型串行推理成本单列；复用旧预测建立R0_U、R0_ordinary。

D1四旧S1固定selected8000权重×四A1 B/C推理路径，对rgb_U/dsm_U各两Val tile：64逻辑单元、16对角线精确SHA复用、48新增tile推理。同权重完整可用/全RGB缺失/全DSM缺失先用一个native512真实Val crop、四策略各检查，四权重共48小批前向的工程一致性核验（不是额外完整tile科学评价）。CPU同图检查也在登记前执行。一致性/绑定不通过停止，不换权重挑初始化。D1完整tile原始计数/预测/first-batch trace保留。

## 5. 固定checkpoint和评价
所有P统一fixed8000主比较，4000仅诊断：三state mean仍记录但不用于选择；旧三state对冻结L可能常数，不能机械以4000代替本轮预先预算。checkpoint每500保存，4000/8000保存单独state；8000复制selected，记录selection=prospectively fixed8000。不在U/E选模。

普通评价实际32条件，另保留原fixed22子集；同8000 checkpoint与输入的22条件全部复用，避免重复推理。U两方向单独评价。保存int64 6×6 CM、逐类TP/FP/FN/support/IoU、Full/NoBoundary、joint raw counts、逐tile预测SHA、配置/源码/输入/checkpoint/mask绑定。科学分区始终用原immutable experts，不能把更新后的own logits当固定anchor。

冻结L在普通32及U逐tile检查非RGB缺失位置与旧S1-0预测相同，F0 state digest训练前后相同；E则与同场景新评S1-0比较。原始CM、tile→pool与joint边际由独立summarize入口复算，不能仅信worker打印COMPLETE。

## 6. E掩码冻结与P7去留
CPU准备在所有新推理/训练之前冻结E mask manifest：
- lines64w8：x%64<8，原点0，竖细线；整64周期缺失12.5%。
- blocks64q25：每64×64格内y/x余数均在[16,48)，32×32缺失块；整格25%。
- 两mask×DSM clean/aux_down4/aux_shift8=6条件；实际边界裁切面积及SHA逐tile保存，不读取标签选位置或扫描形状。
- 两旧参考S1-0/S1-3＋十P=12模型×6×2tile=144新增tile推理；R0复用两参考按同可观测mask拼接。
这些为同Val2上的预注册合成压力条件，不能称独立测试集。候选native tile inference耗时排除fixed-reference建立，R0估计为两参考耗时之和＋另报廉价拼接。

P7同时满足：RGB_U对S1-0≥2pp、对P6/P8/P9各≥.3pp（均两tile正），对R0≥−.2pp；clean/两fullmissing pooled≥−.1pp、所有primary condition×tile≥−.2pp；DSM_U≥−.1pp。E全部6 pooled≥−.1pp、最差tile≥−.2pp、两个clean-DSM新形状≥.5pp且两tile正。具体口径沿规划，没有降低旧门槛。固定候选失败不后验换P3/P5或调宽度/训练预算/seed；仅匹配R0且缺乏成本优势定位工程证据。

Q镜像DSM四组为条件储备，当前没有可运行任务。只有D1固定S1-0同权重B0C0−B1C1的DSM_U≥.5pp且两tile正，且P7/U与E通过，才标记ELIGIBLE_AWAITING_FROZEN_PROTOCOL；否则SKIPPED_GATE。资格不自动启动，另冻结具体DSM方向协议后实施，不把最多14组解释为已派发14组。

## 7. 启动与记录
入口scripts/enqueue_post_s1_support.py --root ROOT --commit EXECUTION_COMMIT。用git show固定提交的入口到zzx下bootstrap；入口复制旧执行快照并逐SHA核对、覆盖本轮14个新执行/协议文件，登记前执行同包CPU检查，创建独立records/research_post_s1_support_<timestamp>_<pid>，nohup启动控制器。重复入口只回报既有登记；部分登记失败需诊断，不另造第二目录。

源码快照、temporary/cache、mask、日志、预测、checkpoint与上传worktree全部在对应zzx目录。状态入口status_post_s1_support.py只读；原始轻量上传入口upload_post_s1_support_records.py，gzip-base64-exact-v1无损编码，512MiB轻量总量/80MiB单文件保护，数组与权重仅server index。完成/失败均可显式上传；上传不会训练或更改旧科学快照，非强制push遇远端冲突停止。

CPU本地使用Torch2.7.1+cpu与合成专家/进程，服务器登记再跑Torch2.2.2+cu121环境CPU检查；尚无真实权重/GPU科学完成观测。预算沿规划33—57h，首个冻结/共享完整作业后校准；CPU记录整理、SHA核对与未知工程差异可影响耗时。重要结果/故障/交接继续写回同GitHub分支并回读。
