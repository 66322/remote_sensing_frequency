# 研究决定：先拆解融合回归，再检验受保护条件补救（2026-10-14）

## 阶段、角色与决定来源
主线仍RGB–DSM条件互补与退化/缺失分割，任务驱动恢复旁支。Phase2完成；用户本轮要求综合两份外部分析规划下一阶段、GPU0/1至少一天并及时回收缓存。用户随后明确要求“按照上述规划安排具体实验”。[科学门禁规划](../protocols/PHASE_24_DIAGNOSIS_AND_CONDITIONAL_HEADS_20261014.md)已落实为[执行包](../protocols/PHASE_24_EXECUTION_20261014.md)，初版用户登记后，18项检查通过、两项IPC路径检查失败，无控制器或科学任务启动；替换目录research_phase24_protected_20261014T193915_2149100已按用户回传登记，最后于20:09观测进入**D1**。[工程修复](../protocols/PHASE_24_IPC_PATH_FIX_20261014.md)只解决通信路径及单次显式技术替换，不改变研究方向、科学预算或失败配方门禁。

## 实验已验证与代码事实
[Phase2结果](../experiments/PHASE_2_RESULTS_20261014.md)和[原件验收](../../records/phase2_review_20261014/verification.json)：Potsdam Fit12/Val2、seed42、NB fg5；匹配两专家，核心4训练48k，B1/B3未派。C=True、L=False，静态clean保护不通过。两个模态专家不是三个seed-only专家；融合头训练时专家冻结，不能归因于DSM梯度伤RGB骨干。

采用同一bestFixed分解：B2在RGB-fault相对bestFixed +4.2481pp，DSM-fault −7.6092pp。oracle−B2不能全部称未利用互补。弱DSM能力/标度/选择作用为待检验机制，单次seed42和两重复Val2仅开发证据。

## 下一研究决定
先复用CM/错误重叠，生成642case联合流/标度诊断，做两fold source→target温度/alpha/小logistic，再补522case固定端点。原专家16k不重训；校准若已解决则不训练复杂头；可部署信号有实际跨tile收益并保护clean/DSM方向后，才进入RGB-anchor信号头与无信号控制。T0 clean头对旧mixed是本轮训练分布控制；最多4小头×8k，原B1/B3门禁不重写，额外seed不自动派。

这种非对称保护是候选解法，仍需评估两方向，不倒写为主线已改为单模态恢复。当前观测/决策类失败只停止这一方案，不否定所有互补或自动转旁支。确认性多seed/独立场地需后续单独登记开放。

## 未采纳建议
像素内交换correctness不改变union，不能作唯一生死gate；改为附属固定完整预测边际的跨像素alignment参照，不能据此估计随机oracle噪声比例。LLM随机多响应研究不能把12–36%/0.096数值迁移到本确定性分割。旧C-OO异协议分数不能作本轮因果锚点；margin单变量无差不代表所有gate不可能；8k→16k小增益不证明永久收敛。外部文本两seed×三模型建议本轮不采纳自动派发。

## 产物决定及当前边界
用户35910文件清理完成回执12:13:25已验收，旧缓存不再在线；confidence诊断需限定再推理，不恢复大缓存。新代码必须实现分批RAM/最后消费者回收，长期仅留原计数、绑定、参数/配置/代码、必要权重与轻量审计。[规则](../protocols/EXPERIMENT_ARTIFACT_RETENTION_20261013.md)。原服务器权重未本地重新hash，L坐标union仍限原服务器证据；保留坐标，不宣称独立验过。

实现口径：原window头与新FP64 post-stitch决策分开；guarded source内层组仅用于源拟合选择，目标全tile评价；T1/T2名义架构一致但有效容量不同，T3统计固定错位256输入像素。0-init仅保证初态，不保证训练后clean；完整保护门禁仍必需。初版18项数值检查和旧差值复算通过，用户服务器又验证这18项通过，但两项IPC失败；修复版本地26项中23通过、3项Linux检查跳过；随后用户REGISTERED输出证明服务器26项全通过无skip，原CPU日志尚未逐字节接收；最新status显示SMOKE12完成并进入D1，依控制流通过真实GPU/CM桥接准入，smoke原件仍待独立验收。工程登记失败不能解释为互补机制或融合配方失败。

此次修复前决定归档[history](../history/20261014_before_phase24_ipc_fix/RESEARCH_DECISION.md)。

最新状态属于工程运行证据，不是新的科学结论。最后观测：2026-10-14T20:09:38.622155+08:00；查询时间20:09:42.751022+08:00。用户回传status/日志，QUEUE=D1、控制器和GPU0/1均LIVE=True；这是该时刻观测，不是实时状态。

SMOKE=12；D1累计393/642，其中10个核心smoke复用，本阶段新完成383/632，剩249。CPU_PENDING=0，查询时无等待中的CPU case；两卡仍正在处理case。当前阶段估计剩0.29218小时（约17.5分钟，约20:27结束）；此估计仅覆盖D1，不覆盖后续分析和条件训练。

D1进入意味着固定控制器的输入、双卡smoke和CM桥接门禁已通过；输入48/48完成。尚未独立接收smoke_pass等原始JSON逐字节验收，不能据控制台状态声称正式机制结论或训练结果。

[最新观测](../../records/phase24_registration_20261014/observation_200938.json)。
