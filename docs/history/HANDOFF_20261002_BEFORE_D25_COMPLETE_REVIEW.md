# 当前交接：D25八组已实现授权，待服务器启动观测

更新2026-10-02，权威分支rebuild-v1-protocol-20260915。用户明确“按上述实验规划进行具体实验”，八组执行已授权，不重复询问授权或资源审计。[此前交接](../history/HANDOFF_20261002_BEFORE_D25_EXECUTION_READY.md)。

D24最后服务器观测2026-10-02T04:06:59.332637+08:00 COMPLETE15/15，原件acd2dbf已上传并复核。[Pair纠错](../experiments/D24_REVIEW_AND_PAIR_CORRECTION_20261002.md)：A1/A3损失开关未生效，相关消融无效，不能称Pair失败。last4/Q强基线有效，QD改善缺失而略损完整；类原型/类别平衡及旧教师区域KD未支持确认，不外推为全部思想失败。

D25已实现，[固定执行提交0c31167d0fdb57f03459ea18981c1ee02bcee9f2](https://github.com/66322/remote_sensing_frequency/commit/0c31167d0fdb57f03459ea18981c1ee02bcee9f2)；[执行说明](../protocols/D25_EXECUTION_20261002.md)、[科学协议](../protocols/D25_MISSINGNESS_OPTIMIZATION_PLAN_20261002.md)、[机器计划](../../records/research_d25_plan_20261002/plan.json)。12合成CPU行为检查PASS、五入口/22快照/Python3.10语法检查PASS，尚无服务器启动/首步/PID/目录观测，无SSH直连。下一步由用户终端一次nohup启动，收到真实输出后只更新观测并查询已有队列。

GPU0 P0普通QD→P2分头→P4共享头投影→P6光学；GPU1 P1真Pair→P3分头投影→P5双共享头平均→P7同模长方向对照。8×4000=32k、seed42、batch16无累积；两H10080GB、RAM/硬盘充足沿用，6h/job、不自动重试/扩展。所有快照/cache/temporary/log/PID/checkpoint/归档在zzx新D25对应目录，主工作副本只fetch。

主问题仍为光学可用时DSM有益融合、退化/缺失能力与负迁移；C1恢复旁支、部分解冻强基线、最终贡献未冻结。D25两个假设为状态共用decoder和完整/缺失梯度干扰，容量/方向幅度/同M0光学对照匹配，Pair技术纠错另判。[文献映射](../literature/D25_OPTIMIZATION_AND_MISSINGNESS_20261002.md)是来源，改写不冒充原论文复现/新颖贡献。

数值screen与梯度机制依据分开；每100步是采样，读原计数/共享范围/方向。最多两条通过后另立seed与真正独立数据确认协议，失败不自动扫参数。Test6禁读，反复Val2和历史Train16暴露held4都不独立final。频率本轮不强制加入，未作永久否定或转向第2章决定。
