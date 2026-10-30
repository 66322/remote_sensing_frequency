# D23 B：八组4000步开发集正式对照

更新2026-10-01。用户要求资源充足时直接推进实际实验，不再新增独立资源测量前置。本轮测量已经完成，[预算原件](../../records/research_d23_b_budget_20261001T145926_658274/evidence_20261001T151324658552_733424/upload_manifest.json)提交54e19cd16416b866bed7b152ba9a3a3f76ac4837，执行b02bb7b。13原文件/SHA通过、196矩阵复算通过，两卡6固定×14条件预测SHA一致，256样本TCAP统计JSON完全一致，CPU27项通过。两卡最后观测15:12:41.571581/15:12:58.837909+08:00，实际789/806秒。不是Val2精度贡献证据。

## 执行内容与研究问题

入口scripts/launch_rebuild_v1_d23_formal.py；每组seed42、固定4000步，冻结D21 R0/M0专家，gate18145参数、专家micro8、gate16、两视图合并loss一次backward；输入/退化/keyed数据流与既定D23协议不变。

| 轮次 | GPU0 | GPU1 |
|---|---|---|
| 1 | TSF | T0 |
| 2 | TS | TF |
| 3 | TCAP | TSF_CE |
| 4 | TSF_shuffleS | TSF_shuffleF |

每组独立12tile训练缓存和256个TCAP统计样本；重新计算正式统计，不复用16步预算权重。训练后评价Potsdam Val2的3_11/5_10、14条件、6固定+该组，保存Full/NoBoundary int64矩阵、逐类计数、harm/rescue、逐tile、预测SHA、源码/配置/专家/checkpoint绑定。主指标NoBoundary mIoU_fg5；Test6禁读，独立final未开放。

研究比较不变：TSF能否超过6固定/T0/TCAP，语义/频率能否产生独立增量，已知DSM缺失回退与精度风险是否受控；全部8组完成才按冻结screen审计。单seed42 Val2属于开发阶段证据，不自动成为论文确认性贡献。频率无增量撤回对应承诺，gate失败关闭具体解法；不自动改阈值/加seed/C1升主线。

本次明确保持既定fixed_final_step_protocol_exception：不以test选模，也不使用Val2反复挑4000步以内checkpoint。最终checkpoint固定final4000，Val2用于开发对照；该例外来源于已冻结D23方案。

## 运行预算与停止

实测含CPU数据读取的最慢组p95为0.743秒；4000步约2972秒，整图评价与初始化另计。已有保守每组估计8519秒（2小时22分），两卡各四组全队列预算约9.5小时，实际可能更短，不是运行结果或精确ETA。

configs/rebuild_v1/d23_b_runtime_20261001.json已承认现有测量，供已有formal接口执行绑定；不启动新probe、smoke或预算流程。每组wall上限3小时、RSS64GiB、GPUallocated32GiB/reserved40GiB、盘32GiB，controller额外30秒停机余量。全队列8组缓存/预测在服务器占用可超过单job限额，预计百GB量级；用户已说明磁盘充足。

源码/输入/config绑定变化、既有GPUcompute占用、非有限损失/梯度、回退失败、资源超限均作为技术失败保留诊断。某组失败不启动新组；另一卡已在运行的当前组继续到完成或其自身超时，不丢弃正在进行的工作。不会按中途精度停止、增加任务或自动续训。checkpoint每100步保存，技术失败保持部分目录，恢复需明确处理评价原件不可覆盖约束。

controller每30秒输出当前组、已用分钟及最后一条日志。PROCESS_STARTED只代表子进程已启动；实际训练由D23_GATE_TRAIN日志证明，完成由formal_complete.json的4000步绑定证明。不将代码READY写成服务器已开跑。

## 文件与回传

用户终端执行，所有快照、runtime_lock、plan、queue_status、logs、jobs/<arm>、Git上传工作树在zzx对应的新research_d23_b_formal_<timestamp>_<pid>目录，保留旧admission/budget及失败记录。

结束后screen_result.json审计所有8组原整数矩阵和跨组/跨卡固定预测一致性。结果与轻量原件自动上传同一GitHub分支；若worker技术失败，也上传已产生的明确JSON/日志，不递归上传缓存/预测/权重。每文件5MiB、总轻量32MiB，超出时保留文件并报告，不截断。非强制推送，凭据仅在服务器终端输入。用户仅回传提交号，助手直接读GitHub。

新增队列5项本地模拟检查通过：完整8组调度、单卡失败阻止新任务并保留另一卡完成、未到4000步拒绝、绑定漂移拒绝、状态原子更新；未在本地启动真实训练。核心/engine27项已在同Torch2.2.2服务器预算快照通过。本次沿用已测量runner/engine/lifecycle/gate源码，不改模型或损失。
