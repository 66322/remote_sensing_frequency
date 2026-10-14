# 当前交接：Phase2.4可执行包待服务器登记（2026-10-14）

## 唯一下一动作
**IMPLEMENTED_CPU_CHECKED_AWAITING_SERVER_SMOKE**。用户已要求具体执行；执行包已完成CPU检查，没有新运行ID、未查询实时服务器、未启动新任务。读[执行协议](../protocols/PHASE_24_EXECUTION_20261014.md)和[科学门禁](../protocols/PHASE_24_DIAGNOSIS_AND_CONDITIONAL_HEADS_20261014.md)。用户用包含此执行包的固定40位SHA取出scripts/enqueue_phase24.py执行；入口先查询既有research_phase24_protected_*，存在即输出原队列而不再派。不要直接运行controller或按旧记录推断GPU闲忙。

## 完成工作与验证边界
13个脚本和1个测试文件实现：唯一登记/双卡case调度、只读输入共享、anonymous memfd、并行计数/源拟合、条件配对训练、状态/整数结果复算/轻量上传。Windows Python3.13.3、Torch2.7.1+cpu：20项中18通过，2项Linux IPC跳过；新D0从原CM复算1164case/640 P-U，六个差值在1e-10内一致。源码编译通过。[实现检查](../../records/phase24_execution_20261014/implementation_audit.json)。真实Torch2.2.2+cu121、memfd跨进程、双卡梯度、12个原CM桥接与吞吐仍待服务器smoke；不写成实验验证或已跑完。

## 任务与资源
D0–D3先做旧计数/642联合诊断/两source→target校准和probe/522扩展。T0 clean头8k；校准不足且probe保护门禁通过才派T1/T2各8k；T1对T2通过再派T3统计错配8k。最多4小头32k，0新专家/额外训练seed。4k轨迹与8k主端点统一评价，不能按年龄捞最优。原B1/B3及L=False不改。

GPU0/1 ≥24h资源窗口，没结束继续，无硬截止。启动检测有效CPU/RAM和两卡空闲，CPU候选16/24/32以同RAM case预热实测；预留控制/裁剪/null资源。原9.792GB规范化输入只读共享；每卡最多2包、clean logit缓存<1GiB、mask LRU8；source sample≤1GiB，无全轮磁盘cache。最后消费者回收；计数复算后自动退役rolling resume和4k临时pth。8k小头暂留待评审，不删原专家/数据/旧记录。

## 已验收旧阶段与研究角色
Phase2运行research_phase2_matched_20261013T151120_1310582，执行e5641e07、上传dc335e0d；最后完成证据2026-10-14T00:39:03.210695+08:00。4核心训练48k，B1/B3未派；309分块/24643原件、3814case/183072 CM及95汇总复算通过。[结果](../experiments/PHASE_2_RESULTS_20261014.md)。用户清理完成回执12:13:25.974504+08:00，35910文件已退役，val/head cache及compact数组不能再假定在线。必要权重/原CM/代码/输入/L坐标保留；这些是最后观测，不是实时状态。

主线仍RGB–DSM双向条件互补与退化/缺失分割，恢复旁支；当前检验DSM条件补救并保护强RGB。B2−bestFixed RGB故障+4.2481pp、DSM故障−7.6092pp；oracle差不等于全是未利用互补。两Val2反复使用、seed42只作开发证据；cross-tile拟合不变成独立泛化。失败只限制当前决策类，不自动否定整个问题。

## 未采纳、门禁和交接要求
不按像素内交换/单margin/附属alignment参照决定路线，不从LLM随机响应比例迁移数值，不跨协议C-OO作因果锚点，不追加两seed/专家/预算。新决策类post-stitch与原window头区别、guarded源样本偏差、T2有效容量和T3包裹范围差异见执行协议。

服务器由用户执行，所有记录在/home/jovyan/zzx对应新目录。无SSH、Test6/held4/final、失败自动重跑。发生技术失败hold并保留原目录，不提供自动替换通道。完成状态PHASE24_COMPLETE_AWAITING_REVIEW；用户运行upload_phase24.py，轻量白名单归档同分支并fetch回读。重要结论及交接继续同步GitHub，补写实际运行ID、最后观测、门禁和剩余不确定性。[原交接归档](../history/20261014_before_phase24_execution/HANDOFF.md)。
