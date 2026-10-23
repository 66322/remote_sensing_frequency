# 共享入口：合并队列启动前修复，待正确环境登记（2026-10-23）

最新执行记录：[启动前故障与修复](experiments/PHASE3_COMBINED_BOOTSTRAP_FIX_20261023.md)。90b9bbe下载包遗漏执行清单导致目标检查失败；本次调用尚未登记训练。合并执行代码改用[e65c6cb](https://github.com/66322/remote_sensing_frequency/commit/e65c6cb0830985461b3cd30e2f43158dd3d858cb)，M2冻结提交与228作业预算不变。服务器现有Torch2.1.2不符合冻结2.2.2+cu121，须先准备独立环境。最后GPU0/1观测为2026-10-23 21:52:05可用，不代表实时状态。

最新研究方案：[连续建筑地图维护中的错误恢复与变化发现](experiments/INDEPENDENT_RESEARCH_ROUTE_20261023.md)。用户要求保留既有研究并寻找独立新路线；助手将旧地图候选细化为优先验证方向，尚未实现、运行或确认为新主线。少量核验纠正漏标保留备选，异步水域时间错配候选依据元数据审计降级。[前一轮期刊扫描](experiments/REMOTE_SENSING_JOURNAL_OPTIONS_20261022.md)保留为来源。

先读[研究决定](current/RESEARCH_DECISION.md)、[交接](current/HANDOFF.md)、[当前状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)，再读[合并队列执行合同](protocols/PHASE3_COMBINED_QUEUE_EXECUTION_20261022.md)、[M2完整协议](protocols/PHASE3_M2_ERROR_CORRESPONDENCE_20261015.md)和[M2执行修订](protocols/PHASE3_M2_EXECUTION_20261016.md)。[研究选择与跨领域方法草案](experiments/POST_M2_RESEARCH_OPTIONS_20261022.md)是候选来源，不等于各臂已得到正结果。

用户本轮已提供预检及启动前失败回执，尚无正式训练注册成功回执；此前要求将原 M2 与条件几何、表征对照以及新公开数据方向写成可一起启动的依赖队列。当前实现为 M2→J→R→T（3DCD）→V（P³），最多 228 作业/5,088,000 更新；由用户以后在服务器终端启动。实际预检已通过，目标检查在登记前失败；新公开数据尚未下载。M2 原核心 108×32k 与科学门禁不变；B90/C81 仍独立条件扩展，不自动插入新队列。

主线仍为 RGB–DSM 双向条件互补与退化/缺失分割，恢复旁支。T/V 是可能形成新问题的探索性方向，不因排入队列而视为取代主线，也不能把小网络开发结果视为超越现有方法。旧 Val2、Test6、held4、final 和新数据公开 test 均封存。只用物理 GPU0/1，中间数据有界内存处理；失败停止，不自动重跑或加种子。原始端点、轨迹和轻量证据在 `/home/jovyan/zzx` 的独立实验目录，重要结论同步本 GitHub 分支并回读。
