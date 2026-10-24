# D30实现与接力检查

用户2026-10-03明确“按上述规划进行，随后加入已进行的队列后面”。D30已实现、执行授权已记录；**待用户服务器执行下面一次nohup命令，尚未收到D30 PID/队列观测，不能写成已在排队**。执行commit固定9db12dfb7ee85dff91dd6c246c7f161b60aca603。本地18项行为检查17通过、1项Linux文件锁检查跳过；服务器启动时自动执行全部18项CPU检查。未在本地或服务器启动训练。

实现范围：48次G0/G1 checkpoint-only固定混合评价；P/R/PR_area/PR_pixel四组静态S结构8000步训练；复用D27 S0/S1原主条件tile记录，补齐全因子及归一化对照。框架继承D27执行快照，不覆写历史目录。科学协议见[冻结设计](../protocols/D30_LOSS_DECOMPOSITION_AFTER_D28_20261003.md)。

一次nohup控制器先验证CPU行为，持续等待指定D28七组技术COMPLETE、summary COMPLETE、controller.lock释放且worker退出，之后绑定原D27 SHA/初始状态，再使用物理GPU0/1。D28科学现象为负不阻断本轮独立诊断；技术失败、控制器意外退出、绑定变化均HOLD，不自动重试。根records/d30_successor.lock避免另一个D30目录重复控制器。若控制器中断，已detach worker保留；恢复必须原commit、原目录、原签名，无存活worker，失败作业不自动重训。

顺序：GPU0 replay_G0、GPU1 replay_G1；两重放完成才进入训练。训练GPU0 P→PR_area，GPU1 R→PR_pixel。专家固定干预只改变混合权重，原三残差专家/锚点/输入可用性回退保持。所有原路由结果直接复用，先核对selected SHA和服务器预测SHA，不新增原路由推理。

数据/增强/初始化/优化器/4000与8000选模/完整评价/固定8000诊断均继承原D27。静态模型以原S1前向构造，loss_variant仅控制目标；S0/S1原目标合成CPU数值及梯度逐参数exact一致（保持原辅助项计算次序）。训练时真实初始化SHA必须等于原16abcd8338a0fae16584d6a70030cb1db5c8a3df741ba7076da77e12e9432281。

每1、100与500倍数步记录CE/aux/protect/recover原值/加权值、分母、类别计数与加权分项梯度范数/夹角。autograd.grad不写优化器.grad、不改变RNG；两view和原损失反传不改变。原混合监控、逐tile/类int64矩阵、联合正确性表与checkpoint签名继续保存。summarizer核对匹配条件的冻结锚点预测SHA，计算保护/恢复交互与预设开发筛选，不复活D27原gate。

验证环境：本地Python3.13.3/Torch2.7.1 CPU，18项中17通过；Linux fcntl检查在服务器d18_dino/Torch2.2.2+cu121启动CPU suite执行。已核对新增源码Python3.10语法。涵盖00/11目标及梯度exact、区域占比与类别均值、空区域、缺失排除、固定混合state_dict/前向/缺失回退、诊断不污染梯度/RNG、等待/失败/两卡分组、原始计数和固定参考绑定、>1MiB记录压缩可逆。CPU合成通过不等于服务器CUDA运行或科学验证。[验证记录](../../records/research_d30_plan_20261003/local_verification.json)。

目录全部在zzx/records独立D30目录内，包括temporary/cache/code/logs/jobs/reused与上传worktree；没有资源探针/新单模态训练/Test6。GPU0/1 H10080GB、RAM/磁盘充足、batch16无累积，约3.5—4.5h自D28释放后计。大型权重/预测本体不传Git；上传器将轻量JSON压缩可逆归档，保留原始SHA及服务器索引，不启动训练。
