# 大内存与并行计算默认工程策略（2026-10-13）

2026-10-13用户要求充分使用内存、并行分析和实验数据预加载，并回传free -h：total1.9Ti/available1.8Ti/used11Gi/free1.8Ti/shared2.3Gi/buff-cache19Gi/swap0。仅用户主机free输出，无独立时间戳/容器quota/affinity回报，不直接当进程可用内存或CPU核数。已将大内存驻留与并行作为后续默认工程策略：CPU case并行初选8（受实际CPU quota/affinity及内存限制并经小规模吞吐校准），工作集按清单一次SHA校验/解压、只读驻留并复用，必要时共享只读cache避免重复副本。缓存预算≤实际可用内存50%，预留数值临时数组和其他任务资源，不为“吃满”强制分配。数值库每进程线程数与case进程数分开控制，不直接把OMP改成最大值。

源码核对：Post-T训练已经fit12全tile驻留、PrefetchedBatches(16,8,4,True)，8线程共享内存crop预取、4batch预取及pin_memory/non_blocking传输；不是每步重读磁盘。后续优化先测data-wait/计算时间，再调预取；保持batch/采样序列/seed/精度/训练预算/验证口径及batch_hash不变。

已新增ResidentArrayCache与recommended_profile工程组件，2项CPU检查通过（16次8线程请求仅装载1次、15命中、数组一致且只读、SHA/修改拒绝、预算/资源限制），尚未接入当前immutable运行或服务器实测；不能写成当前全部预测已驻留。当前只剩47case、约13分钟，决定继续现有2进程而不做第二次接管/全量预加载，避免打断接近结束的队列。新缓存/并发策略用于后续独立执行包，不改变科学主线或新增训练任务。

## 运行前与验收

在对应zzx实验目录保存resource_profile.json：主机RAM、cgroup实际available、CPU affinity/CPU quota、缓存工作集nbytes/来源SHA、case workers、库线程数、预取深度和cache命中统计。先列允许fit12/Val2及原预测/掩码清单，不枚举或预加载Test6/held4/final。大内存允许完整工作集驻留，不自动扩科学任务/seed/预算。

CPU纯统计优先跨case并行，候选8worker，按CPU有效核数与临时RAM降低，8/16选择靠固定小规模计时而非无条件越多越好。当前fast_oracle_evidence通过临时替换module函数实现，在进程内调用，**不能未经改造直接放ThreadPool并发**；模块全局hook要去除/隔离后才能以多线程共用数据，或用只读共享数组/受控多进程。

resident_array_cache.py仅接受显式path/SHA/key，首次流式验证SHA、解压并标记read-only；后续命中检查size/mtime保持、同对象复用。RLock保证线程安全单次装载。按nbytes LRU预算，不因preload返回持有所有淘汰array而突破预算，preload回报all_resident。仅是存储优化，实际数组计算若算法有全局可变状态仍须独立线程安全审计。强完整性由冻结输入/初始SHA及receipt保证；缓存命中不是每次重新全文件SHA。

单纯给此小模块导入并不会自动改变当前执行；下一执行包需显式接入Loader/current/old_prediction/load_mask的等价版本，缓存键含来源与数据变换绑定。输出原矩阵/逐类计数、mask/ckpt绑定和批次hash需一致；按资源预算退回分块缓存时明确记录。

训练保持已有fit12驻留与8线程预取基础，可缓存Val2、评估基础变换与重复参考，但随机增强不能全部预生成后改样本顺序。模型参数更新后不复用旧logits/features。数据已在RAM时仍可能GPU计算主导，必须区分data-wait/CPU transforms/H2D/GPU compute/validation，不只按GPU利用率认定I/O瓶颈。

当前阶段research_phase15_recoverability_20261012T233532_842792/cpu_acceleration_20261013T110244_1189050保持2worker；最后观测见用户记录，不热改源码，不自动新训练。完整轻量原件包括受控停止/真实等价/新代码/资源记录后科学验收。
