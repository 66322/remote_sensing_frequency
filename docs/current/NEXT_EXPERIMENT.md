# 下一步：一次nohup启动已授权的D26九组

更新2026-10-02。固定实现20ff8b3e49d187afaa5a226ceb0e9be6a5cdbfed；[执行指令](../protocols/D26_EXECUTION_20261002.md)，[机读配置](../../records/research_d26_plan_20261002/plan.json)，[CPU检查](../../records/research_d26_plan_20261002/local_validation.json)。当前已实现/检查，**没有服务器启动观测**。

1. 在既定服务器root一次新建records/research_d26_bidirectional_<timestamp>_<pid>并nohup启动固定九组，两GPU动态领取；复用P6/D15 checkpoint，batch16无累积，不另做资源/预算探针或单模态训练。
2. 回传controller PID、目录、D26_STARTED两行，之后从本目录status查看最后观测时间、阶段、step和窗进度。正常首batch自动验证专家/交互梯度，异常保留日志，不自动缩batch/加累积/重试。
3. 每组8000，4000/8000以三状态Val2均值选模；selected22条件＋固定8000十主条件诊断，全保存int64矩阵/计数/预测和checkpoint绑定。首正常完整任务结束后估计ETA，不声称开始前精确耗时。
4. 九组结束查看screen_result.json、results.csv和失败尾日志，再运行upload_rebuild_v1_d26_records.py上传轻量原件；不再贴大量输出，由GitHub直接读取和独立重算预设门槛。
5. 比较XSF与B0/CAP/X/J0及S/F消融/打乱，分别报告完整、双方退化/全缺失/局部缺失和双方独有正确区域；最多一条通过后另立多seed/独立来源协议。没有通过不自动扫参数或增budget，不重开D23—D25旧配方。

主问题仍双方互补，C1旁支，章节/贡献未冻结。两单模态专家异构和历史held4暴露保留；Test6禁读，Val2开发不独立泛化。服务器状态待真实回传，不能把“代码发布”写成“运行中”。
