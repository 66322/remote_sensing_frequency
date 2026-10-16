# Phase3-M2-A：具体执行与精简结果交付（2026-10-16）

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent，plan + implementation。
- 版本：phase3_m2_execution_v1。设计基于83e3206329372e778c5987d9abd785d9efcca5fe；M1验收基准仍为5565f93b2e62be22291583cc876f86ecb56c52dc。
- 状态：CORE_IMPLEMENTED_LOCAL_CHECKS_PASSED_NOT_SERVER_LAUNCHED。服务器由用户执行；尚无M2运行回执、实际fold表或实时GPU空闲证据。
- 这是M2完整协议的执行补充。以下明确修订优先于v1中对应条款；不是新实验结果。

## 1. 核心训练已具体化

每个外层划分×整系统seed：1个train8 RGB参考、4个train6 RGB交叉拟合教师、7个train8 DSM臂。三划分、seed42/17/2026，共108训练、每个32k、batch16，总3,456,000更新。全部从已绑定公共DINO预训练开始，不读取旧微调模型。

七臂仍为D0、DSelf、DClean、DF、DShuffle、DEntropy、DMix。R1+A1、stem及后4个block训练、前8个block冻结但允许梯度穿过。RGB维持普通范围。学习率沿M1按进度映射：warmup从100映射至200更新，其后线性衰减到32000；encoder/stem初值2e-5，其余2e-4。8k/16k/24k/32k保存外层计数，32k为唯一主端点。

`phase3_m2_data.py`在读取标签前仅查Fit12的RGB影像头，按预设坐标规则固定fold；缺地理信息时明确采用自然tile顺序回退。已知重叠即停止，即使其他tile元数据缺失也不忽略已知重叠。精确tile表在服务器`folds.json`中冻结并进入运行绑定；不伪造本地尚未读取的坐标。

实际DAG由`phase3_m2_common.jobs()`生成，与108作业计划一致；教师必须未训练过学生当前tile。每个crop的teacher来源由冻结的inner_pair表和确定性样本流绑定。不同处理臂的初始化与完整样本流摘要必须一致。

## 2. 四项科学修订已在代码中固定

1. **DMix的平均梯度尺度匹配。** 原目标为0.5 CE(pD,y)+0.5 CE(0.9pT+0.1pD,y)。对DSM的CE梯度系数为c=0.5+0.5×0.1pD(y)/(0.9pT(y)+0.1pD(y))。现将原loss除以有效像素平均c，分母stop-gradient。保留相对困难分配，去除额外全局梯度缩放；记录原始c均值和归一化权重分布。这是归一化DMix控制，不冒称完整竞争方法。
2. **G2增加DClean。** DF−DClean的主融合mIoU三seed平均至少+0.2pp，每seed均>0；与其他非D0对照的门槛相同。若clean教师已同样兑现，关闭“退化教师有额外实用价值”的主张。
3. **H2增加受损区要求。** DF−DClean的DSM补救率，在RGB-down4的all及damaged两个区域，分别要求三seed平均至少+0.3pp且每seed>0。H1/G1与H2分别登记；一般对应性成立、退化特异性不成立时保留前者，停止本轮退化特异扩展。
4. **G3范围明确。** 主概率融合、NoBoundary、中央内缩512。clean/all、RGB-down4/healthy、DSM-down4/all、DSM-shift8/all四个保护项目均要求每seed池化DF−D0≥−0.2pp；每项目每tile的三seed均值≥−0.5pp。这个tile均值底线比旧M1逐seed×tile的−0.2pp宽松，覆盖范围不同，不能称通过旧门禁。

H1：DF相对D0/DSelf/DShuffle/DEntropy的RGB-down4 all区补救率，均值≥+0.5pp、每seed>0。G2对D0均值≥+0.3pp，对其他指定对照均值≥+0.2pp，所有seed>0，9个fold×seed至少7个DF−D0为正。G4仍要求6个异seed换配至少5个为正；三个未见退化各自三seed平均>0、每seed≥−0.2pp。G0、H1/G1、H2、G2–G4全部满足才允许登记后续反向阶段；这是实用推进判断，不是显著性标准。

## 3. 掩码与数值合同

评价保留原6000×6000 structured_v0生成器，4 family×5 realization，25%面积；为本轮Fit12外层tile重新生成，不能冒充M1旧Val2面板。生成规则与ID固定，不按分数重抽。matched的标签辅助属性和空间形态混杂如实保留。掩码设计摘要保留服务器。

训练crop为512，旧6000生成器不能直接套用。本执行版明确采用裁剪尺度实现：pixel精确四分之一；random为32像素块均匀抽样；gradient为同网格按DSM梯度倾斜抽样；matched使用同一次gradient抽样的逐类像素配额，以独立随机块优先次序选择相同逐类数量。matched配额精确相同，但边缘形状并不与gradient完全一致。这是裁剪版四类角色，不能写成旧大图掩码形态的完全复现；不新增训练臂。

DF/Clean/Shuffle/Entropy/Mix的teacher视图在裁剪预取线程中产生，学生DSM始终clean。损坏条件、掩码、置换键均与crop采样键分离，同一crop重复出现保持相同条件与置换；各对照共用同一DF视图来源。Shuffle/Entropy每类×边界bin的q集合精确守恒，ignore不参与。

评价为原生512/stride256、FP32窗口顺序累加、FP64后处理，主概率混合0.9RGB+0.1DSM。alpha七格全保留，logit混合仅敏感性参考。noise005/blur2是清单中Gaussian noise std0.05/blur sigma2的代码简称。

## 4. 并行流水与内存上限

- GPU仅物理0/1，实际进程按启动观测UUID绑定。注册前、准备完输入后再次检查外来计算进程和空闲显存；每卡有未知占用或不足40GB则不训练，不终止任何外来进程。
- 两个持久GPU worker共享就绪队列。依赖单元内固定随机次序，优先参考和教师；有就绪推理先做推理，CPU背压时继续其他训练。
- CPU采用Linux fork进程池，最多32，按有效CPU额度减去训练预取余量自动降低，每进程数值线程1。来源：2026-10-15合成原计数基准32进程/16线程吞吐3.622倍，不是完整影像ETA承诺。
- GPU交出memfd所有权后即可继续。CPU只经IPC领取FD/索引，完整数组不通过pickle复制；每个counter内部按128行处理。
- 每次只保留一个外层tile的21份DSM clean预测、3份clean RGB及最多2个故障RGB案例。保护诊断按有限在途预测消费。不是整个fold/全轮磁盘logit缓存。
- 所有必要CPU计数与后续GPU任务并行。有界背压防止内存失控，不承诺所有CPU在没有输入时仍有工作。
- 首批正式训练期间，CPU同时完成全部60个评价掩码设计的可行性检查，最多8个高内存生成任务同时运行。只保存紧凑图元和确定性种子，评价时精确重建并核对设计，不重复昂贵的匹配搜索，不把12个tile的掩码长期堆在内存。
- 预测最后消费者退出即释放；成功作业在32k端点及四个年龄外层计数落盘后退役rolling优化器，必要端点保留。失败状态保留，不自动重试。

每作业1000步后记录稳定sec/update及剩余纯训练小时，排除验证插入时段；推理、计数、上传成本另列。不得用更新数倍数冒充真实耗时。

## 5. 结果交付简化

服务器完成边际、fallback、ROI、样本流和端点完整性检查后生成：

- `REPORT.md`：可读结论及主结果表。
- `summary.json`、`gates.json`、`metrics.csv`：状态、预登记判定、各面板/区域汇总。
- `F0_counts.jsonl.gz`、`F1_counts.jsonl.gz`、`F2_counts.jsonl.gz`：每tile×RGB seed×DSM seed×臂×条件的NoBoundary充分整数统计，mask先池化；保留所有正负结果和alpha曲线。
- `server_evidence_index.json`、`manifest.json`：服务器原件位置、端点哈希及交付索引。

逐mask原件、完整辅助统计、训练样本流、轨迹、端点留在服务器，不逐轮下载到本地。上传以Git Data API一次原子提交完成，不fetch/clone旧Git历史，不切数千小块；检查Git对象返回ID，只回读三个小JSON。通常只读报告/汇总即可讨论，出现实际矛盾才定向查服务器原件。

上传只使用现有环境/gh/系统Git凭据，不提示输入、不索要、不输出Token。无现有凭据则写`upload_pending.json`，保留已整理的交付目录。上传失败只续传既有文件，不重训、不重推理。B/C不因网络失败而派发。

结果提交会同时把共享入口指向本run报告。仅当当前状态仍是本执行包的就绪版本、或明确登记为本run时才更新；若另一个实验已接管入口，只追加结果，不覆盖后续交接。

## 6. 启动与当前边界

入口：`scripts/bootstrap_phase3_m2.py --root <固定项目根> --commit <完整执行提交SHA>`；加`--inspect`只检查Fit12影像头和GPU，不注册run。启动脚本复制已验收M1恢复run内绑定源代码，只下载本轮少量新增文件；不恢复M1队列。

仅当GPU与目标Linux检查通过才创建/启动新的`records/research_phase3_m2_<真实时间>_<PID>`。断开终端不中断已启动控制器。重复入口只显示既有run，不重复训练；已失败run不由相同入口自动覆盖。

本执行版落实A核心。B的90训练须在A全部门禁通过后冻结反向输入归一化、损失与评价的具体合同，再登记独立执行提交；当前不自动派发。C的81训练仍为第二编码器预算储备。总279上限未扩大。不会为了保持卡忙而运行不满足条件的实验。

当前本地16项检查15通过、1项Linux真实FD传递待服务器；目标CUDA、真实输入/地理fold、现场显存和端到端吞吐未验证。模型构造和真实梯度检查并入首个正式更新，不额外训练。助手无服务器访问，不宣称已启动。
