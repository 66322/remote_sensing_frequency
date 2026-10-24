# 下一步：落实Phase2.4规划的执行包（2026-10-14）

当前仅[规划登记](../protocols/PHASE_24_DIAGNOSIS_AND_CONDITIONAL_HEADS_20261014.md)，**PLAN_ONLY_NOT_IMPLEMENTED_NOT_ENQUEUED**。用户目前先规划，不启动新队列；旧Phase2计算/35910文件清理已完成，删除旧执行清理动作。

若用户随后要求按规划执行：
1. 检查原队列/锁，绑定已完成Phase2专家/头/输入/mask、原CM和retirement记录；不重启原队列，不假定已退役大缓存存在。
2. 新执行包先实现GPU0/1动态case队列、原输入只读共享、直接联合计数、source/target分离、原始CM离线重算及有界RAM/消费者即时回收；GPU参数常驻，避免整轮磁盘cache与按头重复backbone forward。
3. 12个真实case先在两卡做数值/CM/availability等价、异常清理和吞吐验收；CPU16/24/32实测选型、有效CPU/RAM配额确认，报告分阶段ETA/显存/RAM/磁盘峰值后冻结snapshot与科学manifest。工程变更不能静默改精度/微批/指标。
4. D0–D3先做旧计数、642联合诊断、两fold温度/alpha/logistic及522补充端点；T0 clean分布对照与条件T1/T2/T3按具体门禁，最多4小头32k，不自动救原B1/B3或加seed。校准足够则停止复杂方法分支；部署信号失败则限定停止当前决策类。
5. 服务器由用户执行nohup，所有记录在/home/jovyan/zzx对应新实验目录。GPU0/1资源窗口≥24h可续，取消一天硬截止；门禁失败不为凑时长加无意义任务。原始计数、轻量参数/来源/轨迹与必要模型保留，最后消费者完成即释放临时张量。上传只用轻量白名单，同分支回读核验。

研究仍RGB–DSM双向条件互补与退化/缺失分割，保护强RGB的非对称操作只是候选解法。独立泛化/确认性多seed未开放；禁止Test6/held4/final、SSH及自动配方重试。旧D23/其他历史大型产物继续按独立依赖审计处理，不由新实验规划扩大删除范围。[存储执行规则](../protocols/EXPERIMENT_ARTIFACT_RETENTION_20261013.md)。

旧下一步归档[history](../history/20261014_before_phase24_plan/NEXT_EXPERIMENT.md)。
