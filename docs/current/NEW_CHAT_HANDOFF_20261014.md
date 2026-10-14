# 新对话接续：Phase2.4原队列（2026-10-14）

以GitHub 66322/remote_sensing_frequency 的 rebuild-v1-protocol-20260915 分支最新内容为准；先读docs/START_HERE.md，再读docs/current/RESEARCH_DECISION.md、HANDOFF.md、PROJECT_STATUS.md、NEXT_EXPERIMENT.md，及本文件。勿依赖旧聊天记忆或历史开场指令GPU0-only。

## 原队列与最后观测
服务器目录 /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase24_protected_20261014T193915_2149100。
执行代码5a84f0eacabe5d6f1c7ed1638e6a9291c58e151f，控制器2149894，两GPU进程2149964/2149965，日志nohup_20261014T193920570637.log。执行快照固定，不用后续文档提交替换运行代码。
最后观测：2026-10-14T20:28:16.847139+08:00；查询时间20:28:17.018087+08:00。用户回传status及60行日志尾部，QUEUE=D2、控制器和GPU0/1均LIVE=True；这是该时刻观测，不是实时状态。

SMOKE=12；D1累计642/642完成（复用10个核心smoke，本阶段新完成632/632）。D2已完成8/642，CPU_PENDING=1。GPU0为TRAIN:T0，GPU1为INFER；T0在20:28:15.718518观测1140/8000更新，loss=0.1307082772，remaining_train_hours=0.1445449292（约8.7分钟），仅覆盖T0剩余训练，不含端点评价。D2阶段ETA=None，不估计整轮结束时间。

T0是协议必做的clean训练分布控制，可与D2并行；本输出未给T1/T2/T3门禁结果或派发证据。GPU0旧progress/runtime停留在20:26的D1推理，不能用旧文件误判当前GPU0空闲或卡住；当前状态和T0更新时间表明正在训练。两卡峰值allocated约5.54GiB，CPU基准选择32进程、每进程数值库1线程；日志尾部只有配置预期的xFormers警告和D1进度，未见错误，但并非全日志验收。
[记录](../../records/phase24_registration_20261014/observation_202816.json)。

## 第一动作
请用户只读查询原目录status_phase24.py和新nohup日志。无SSH，不重复登记、不重新启动，不对完成阶段重复派发。若technical hold，接收错误原件并检查实际执行链，不自动重跑失败配方。当前无本轮新的科学结论，smoke原JSON尚待独立轻量原件验收；不得把控制台通过倒写为论文正式结果。

## 研究与执行约束
主线RGB–DSM双向条件互补和退化/缺失分割，恢复旁支。Phase2匹配专家已完成，C=True、L=False、B1/B3未派发；旧结论继续按原证据，不把一个候选头失败扩大为研究问题不成立。Phase2.4先D0–D3诊断/source-only校准，T0 clean8k必做；只有门禁通过才T1/T2各8k，再条件T3 8k。最多4小头32k，0新专家/训练seed；GPU0和GPU1可用，≥一天资源安排，无24h硬截止，不凑时长。用户目前无需单卡释放管理。
Val2/seed42开发证据；无Test6/held4/final，不自动加seed。读取[执行协议](../protocols/PHASE_24_EXECUTION_20261014.md)、[科学门禁](../protocols/PHASE_24_DIAGNOSIS_AND_CONDITIONAL_HEADS_20261014.md)、[IPC修复](../protocols/PHASE_24_IPC_PATH_FIX_20261014.md)，按链接核对Phase2完整结果、Phase1.5和早期实验。

## 资源与保留
输入48数组9.792GB只读共享RAM；两卡最多各2匿名包（每包2.304GB），最后CPU消费者后释放。CPU基准16/24/32结果SHA一致选择32，不能误读为全局1线程。没有整轮全图logits/特征磁盘缓存；只留必要混淆矩阵原计数、绑定、配置/代码、参数、轨迹、必要端点权重及轻量审计。上一轮35910缓存文件已退役，不恢复旧cache，不擅自删除数据/必要权重。新产物清理须验证完成状态、统计可重算、轻量归档和路径范围，所有记录/临时均在zzx对应实验目录。

## 后续验收
完整结束后由用户显式执行upload_phase24.py；先核验GitHub是否已上传和原上传进程，勿重复启动。接收轻量原件，核对manifest/SHA/代码执行链/完成标记/计数并离线复算，分析模块、双方向保护与训练轨迹；再决定下一轮。重要结论和交接同步同分支并回读报告提交链接。禁止用旧观察推断实时队列；整轮6–12/24–36小时估计仅粗预算，没有后续实测不能承诺。
