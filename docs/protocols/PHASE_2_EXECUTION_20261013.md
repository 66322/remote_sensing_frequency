# Phase2执行包（2026-10-13）

状态 READY_FOR_USER_LAUNCH / SERVER_GPU_SMOKE_REQUIRED。用户已授权按Phase2规划执行；当前只在本地CPU核验，未访问服务器、未登记新队列。核心4训练48k、条件性最多6训练64k，GPU0/1，无24h截止；任何技术失败HOLD，不自动重试配方/新seed。

## 科学协议与实现澄清

[完整设计](PHASE_2_MATCHED_COMPLEMENTARITY_20261013.md)为科学规则；新源码scripts/phase2_*.py、control_phase2.py、model/phase2_matched.py落实参数、数据流、静态/动态头、C/L/剩余差距及保护。两专家同预训练与随机头、共同fit12 stream、tail4+投影+完整分类头，各16k；下游固定16k，不择优换年龄。B0/B2固定8k后才判动态，B1/B3门禁通过才派发。

以下澄清在新运行前锁定，不是结果后变更：
- down4沿d23_engine.resize_restore，bilinear且下采样antialias=True、上采样align_corners=False；此前设计文字“area”不准确，本包使用经审计的既有bilinear实现。
- head网格为128×128；原输入上5×5加权统计按reported availability归一化，再平均到该网格。两个熵来自原窗口专家概率；L使用这些实际头输入熵差的最近邻重建与均匀重叠平均，不另用拼接后softmax熵冒充同一信号。
- 专家训练bf16，固定expert缓存与评价FP32/TF32；小融合头用FP32（缓存FP32），所有四头一致。microbatch8，512/stride256，不静默调batch或精度。
- L支持量中的10/20按realization ID聚合四族和两破坏；各tail每tile至少10000不同坐标。重复坐标/掩膜不是独立地点。
- healthy为17×17扩张mask之外，与旧协议一致；空支持记NA。宏平均只对有定义的同支持指标计算；不把空区域变成0或看结果后改区域。
- 8k面板322场景；16k原面板1122场景，外加旧22条件中非clean的21×2=42，合计1164。B0/B2/B1/B3复用16k专家窗口cache；传感器物理输入相同而reported flag不同的P-M/P-U zero共用expert cache。
- Phase2.0旧160份D与120份pixel dose原计数在CPU复用；720份内部身份回执不重跑GPU，不伪造新增KL测量。

## 调度、资源与停止

enqueue_phase2.py仅允许一个research_phase2_matched_*目录；重复调用打印既有目录状态，不启动第二份。先检查原Phase1.5完成、旧owned进程退出和controller锁释放。继承旧不可变code_manifest逐文件核验，再从固定Git提交覆盖新文件，所有执行/缓存/临时文件在新records目录下。

CPU准备：检查源配置/划分/DINO仓库commit及dirty diff；完整源影像SHA校验一次，fit12/Val2解码、归一化为只读npy，预存Val2 down4。随后GPU0/1真实smoke与旧CPU计数分析并行；smoke检查公共初值/参数清单/真实反传和低分辨率重建及head回退，通过后从公共初值开始正式训练。

A_RGB GPU0 / A_DSM GPU1；每卡自己的4k验证，无每step屏障。完成后逐步核验16000条batch_hash。两卡共同做8k/16k冻结面板；每案例写磁盘紧凑原件后立即交CPU进程计算CM，不传大数组经IPC。每卡CPU池为resource_profile.analysis_workers的一半，合计初选最多16，BLAS/OMP/MKL各1线程。

C/L分析与双卡8000步head-cache准备并行。B0 GPU0 / B2 GPU1，再评价和静态后门禁；通过后B1 GPU0 / B3 GPU1。所有头用相同cached stream，核对整条hash。不可通过门禁时直接汇总4训练结果，不转另一方法。

内存/IO：GPU训练每卡最多8 crop线程、8 batch pin预取；输入mmap只读且页缓存复用，cache预算256GiB且≤实际可用内存50%。head读前8个batch并行预取，所有SHA在单次读入字节上校验，避免每batch双重磁盘扫描。冻结expert原window logits保留128网格，预测用3bit标签、availability用bit pack无损保存；L阈值先在FP32计算，再保存精确尾部类别，不用float16近似熵改变0.25阈值。GPU间shared-cache用文件锁与原子发布，已校验cache不每次全文件重hash。

启动要求≥32GiB实际可用内存、GPU0/1各≥16000MiB空闲及600GiB可用磁盘预留；这是为不可变cache和证据预留，1.9TiB主机内存不能替代磁盘检查。核数按affinity及cgroup quota，内存按MemAvailable与cgroup上限。未满足即准备HOLD，没有训练启动。当前用户RAM报告足够，但没有新磁盘/显存/CPU quota实测。

24–48小时只是资源安排；不在24h杀任务，不为凑时长扩实验。进度记录steps/loss/data_wait/elapsed/显存峰值；controller每2秒心跳并记录CPU/GPU依赖阶段。任务失败终止同波仍运行的owned worker，保留已保存checkpoint/日志；没有自动续跑、失败配方重试、增seed或24h watchdog。外部中断后保留目录，诊断并制定显式恢复方案，不重复enqueue。

## 查询及归档

启动回报PHASE2_REGISTERED包含新目录和PID，PHASE2_LOG给日志。只读查询：
python -B DIR/code/scripts/status_phase2.py --directory DIR
同时查看DIR/nohup_*.log、DIR/logs/对应worker.log、jobs/*/progress.json。旧目录/旧PID/旧观测不能当当前进度。

PHASE2_COMPLETE_AWAITING_REVIEW且controller/worker退出后，用户前台运行：
python -B DIR/code/scripts/upload_phase2.py --directory DIR

上传一个精确JSONL gzip流，按256KiB压缩字节分成ASCII base64块（每块约350KiB），保留全原始字节/逐file SHA/索引，manifest/summary可直接读。原始大数组、checkpoint及完整log留服务器并在回执索引，不提交完整继承源码。认证失败重跑同一upload命令复用已提交worktree，不重新生成证据或实验。不force push。

本地10项CPU检查通过：匹配参数/初始化/反传；head回退和信号消融；可观测输入有限且无metadata；预算与mask库存；bitpack无损；流hash；训练配额；正确先pool CM；不合法专家oracle与availability oracle区别；C/L支持量、both-wrong分母及静态吸收后停止动态训练。13个新增Python文件语法检查。真实Torch2.2.2+cu121、DINO/checkpoint/数据/GPU数值检查由服务器smoke完成；CPU PASS不写成正式实验结果。

## 首次GPU smoke技术修复

2026-10-13首次两卡smoke失败在CUDA确定性NLLLoss，正式训练未派发。使用等价classwise log_softmax/where CE保持严格确定性与原目标；原目录保留、仅显式CE专项技术替换可新建目录。此专项例外不开放一般失败配方重跑。12项CPU检查通过、真实GPU检查待用户执行。[诊断、修复及替换门禁](PHASE_2_CE_TECHNICAL_FIX_20261013.md)。
