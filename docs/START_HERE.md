# 共享入口：M2 Python3.9导入故障已定位，待CPU兼容预检（2026-10-24）

最新执行记录：[Python3.9导入故障和CPU预检](experiments/PHASE3_M2_PY39_IMPORT_FAILURE_20261024.md)。用户2026-10-24回传summary/失败节选（此次查询未带时间）：M2 INCOMPLETE_NO_RETRY，0/108完整端点、0评价案例、0个progress.json；63个failure均报unsupported operand type(s) for |: type and NoneType。展示的完整堆栈位于Python3.9加载DINOv2 attention.py的float | None注解，在make_model导入阶段，尚未进入该作业优化器构造或训练循环。全部63个原始堆栈及无更新产物仍由预检逐项核验。 下一步仅执行CPU模型导入/公共权重预检：原目录repairs下生成带逐文件Git blob/原始SHA/副本SHA的Python3.9兼容副本，仅添加延迟注解声明且可执行AST一致。原DINO仓库、M2源码/配置/失败状态和权重不改。不读数据集、不做前向/反传、无GPU、无训练/重试控制器。真实目标模型构造/权重加载尚未验证；7项本地检查及Python3.9语法解析通过。 两控制器停止/GPU空闲最后观测08:38:13，不能视为实时状态。

最新研究方案：[连续建筑地图维护中的错误恢复与变化发现](experiments/INDEPENDENT_RESEARCH_ROUTE_20261023.md)。用户要求保留既有研究并寻找独立新路线；助手将旧地图候选细化为优先验证方向，尚未实现、运行或确认为新主线。少量核验纠正漏标保留备选，异步水域时间错配候选依据元数据审计降级。[前一轮期刊扫描](experiments/REMOTE_SENSING_JOURNAL_OPTIONS_20261022.md)保留为来源。

先读[研究决定](current/RESEARCH_DECISION.md)、[交接](current/HANDOFF.md)、[当前状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)，再读[合并队列执行合同](protocols/PHASE3_COMBINED_QUEUE_EXECUTION_20261022.md)、[M2完整协议](protocols/PHASE3_M2_ERROR_CORRESPONDENCE_20261015.md)和[M2执行修订](protocols/PHASE3_M2_EXECUTION_20261016.md)。[研究选择与跨领域方法草案](experiments/POST_M2_RESEARCH_OPTIONS_20261022.md)是候选来源，不等于各臂已得到正结果。

用户已提供登记、M2前置检查失败及随后原目录修复派发回执，最新回执确认两控制器已停止；此前要求将原 M2 与条件几何、表征对照以及新公开数据方向写成可一起启动的依赖队列。当前实现为 M2→J→R→T（3DCD）→V（P³），最多 228 作业/5,088,000 更新；已登记队列在M2执行不完整后停止，后段未放行。公开catalog尚不存在，真实新数据未验收。M2 原核心 108×32k 与科学门禁不变；B90/C81 仍独立条件扩展，不自动插入新队列。

主线仍为 RGB–DSM 双向条件互补与退化/缺失分割，恢复旁支。T/V 是可能形成新问题的探索性方向，不因排入队列而视为取代主线，也不能把小网络开发结果视为超越现有方法。旧 Val2、Test6、held4、final 和新数据公开 test 均封存。只用物理 GPU0/1，中间数据有界内存处理；失败停止，不自动重跑或加种子。原始端点、轨迹和轻量证据在 `/home/jovyan/zzx` 的独立实验目录，重要结论同步本 GitHub 分支并回读。
