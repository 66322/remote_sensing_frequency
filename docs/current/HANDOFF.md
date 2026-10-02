# 当前交接：D27十组已实现，按授权接在D26之后

更新2026-10-02；研究可行性探索，最终贡献未冻结。用户明确“按照规划进行实验，添加到已有实验后面，之前跑完就进行这组”，已授权十组80k更新。GPU0/1 H10080GB、RAM/磁盘充足、nohup、batch16无累积、zzx对应目录均为已知约定。

最后上传的服务器观测仍为2026-10-02T22:22:14.689169+08:00：D26 RUNNING、COMPLETE1/9；没有更新实时PID信息。 原D26目录research_d26_bidirectional_20261002T191253_1513109，固定52f94388b1a9c7557e9ef533075661139cd55eda，原九组不变。[B0部分复核](../experiments/D26_B0_PARTIAL_REVIEW_20261002.md)：clean+0.726782pp、down4+2.017157pp，但DSM错位3_11−0.496337pp。其他完整结果未收到，不能宣称新机制。

[D27方案](../protocols/D27_SAFE_ROUTING_PLAN_20261002.md)、[实际执行说明](../protocols/D27_SAFE_ROUTING_EXECUTION_20261002.md)、[固定plan](../../records/research_d27_plan_20261002/plan.json)与代码已实现；[本地验证](../../records/research_d27_plan_20261002/local_validation.json)14行为检查通过，30文件独立快照检查通过，11文件Python3.10语法、全部五入口可加载。服务器nohup尚未观测，本地CPU不算GPU运行/精度。

十组S0/S1/G0/G1/L0/L1/C0/C1/L1-sh/C1-sh，每组8000。G0/G1先运行；冻结现有RGB/DSM原专家，三个轻量残差专家；静态/图像级/局部/类别路由×CE/保护恢复目标及打乱。每个job只接收自己的GPU。新controller等待原D26九个job终结及旧controller锁释放，才领取GPU0/1；不修改D26记录/worker/queue，不重复资源审计。

服务器一次nohup启动新launcher --parent原D26目录 --directory固定records/research_d27_safe_routing_after_d26_20261002T191253_1513109；具体完整指令按本次交付的执行SHA。不再等待单独许可或重问资源，但无SSH，仍由用户终端执行。看D27_WAITING_D26是正常排队，不是挂住；D26结束后输出D27_PREDECESSOR_FINISHED和D27_STARTED。已有plan目录不能重新创建并重复排队；中断后依执行说明同commit恢复。

执行前冻结细化：保护/恢复/专家辅助权重各0.1；first clean fit统计存checkpoint；所有专家dense计算、零残差/均匀route初始化，500步起学习路径须活跃；类别条件每sample keyed随机置换，局部场半图shift；局部伤害评估boundary16邻域；额外2项present-DSM诊断不选模。24条件评价保留原矩阵/联合计数、预测、绑定，五入口完整。没有新贡献确认。

主问题优先级按用户：安全融合→动态专家选择→局部/类别适配；双方信息/退化与缺失保留，缺失结构回退不冒称补偿精度。D27:C1是类别候选任务名，与历史第2章恢复C1旁支不同。D23/D25具体失败配方继续关闭。频率待D26独立增量；STARS缺失补偿另立问题；GLFRNet原文未读，不据其定模块。Test6禁读、Val2/历史held4不独立final。共享以GitHub为准，完成后现有D27上传脚本直接上传长轻量原件，weights/预测留服务器索引。
