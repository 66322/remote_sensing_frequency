# 共享入口：M2执行不完整，队列已停止，待失败堆栈（2026-10-24）

最新执行记录：[M2停止取证](experiments/PHASE3_M2_INCOMPLETE_20261024.md)。最后服务器观测2026-10-24 08:38:13+08:00：M2 PID2690788和合并PID2690789均Zs/defunct，GPU0/1均0MiB且无计算进程。M2于08:36:44.670358报告INCOMPLETE_NO_RETRY；合并于08:37:36.280856报告STOPPED_NO_AUTOMATIC_RETRY，原因M2 did not finish as server-checked。12/12输入准备于08:35:40.299463完成。此为最后观测，不是实时状态。 memfd实际libc后端探针及原16项检查已通过。G0完整性未通过时，其他性能门禁为False不能作研究阴性。当前未回传原始作业堆栈，具体错误、完成端点及失败前更新数未知；先读publication/summary.json、failures/*.json和jobs/*/progress.json。xFormers警告、合并下游异常和上传认证缺失均不能据此确定为训练根因。 下一步只读取证，不再次启动。

最新研究方案：[连续建筑地图维护中的错误恢复与变化发现](experiments/INDEPENDENT_RESEARCH_ROUTE_20261023.md)。用户要求保留既有研究并寻找独立新路线；助手将旧地图候选细化为优先验证方向，尚未实现、运行或确认为新主线。少量核验纠正漏标保留备选，异步水域时间错配候选依据元数据审计降级。[前一轮期刊扫描](experiments/REMOTE_SENSING_JOURNAL_OPTIONS_20261022.md)保留为来源。

先读[研究决定](current/RESEARCH_DECISION.md)、[交接](current/HANDOFF.md)、[当前状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)，再读[合并队列执行合同](protocols/PHASE3_COMBINED_QUEUE_EXECUTION_20261022.md)、[M2完整协议](protocols/PHASE3_M2_ERROR_CORRESPONDENCE_20261015.md)和[M2执行修订](protocols/PHASE3_M2_EXECUTION_20261016.md)。[研究选择与跨领域方法草案](experiments/POST_M2_RESEARCH_OPTIONS_20261022.md)是候选来源，不等于各臂已得到正结果。

用户已提供登记、M2前置检查失败及随后原目录修复派发回执，最新回执确认两控制器已停止；此前要求将原 M2 与条件几何、表征对照以及新公开数据方向写成可一起启动的依赖队列。当前实现为 M2→J→R→T（3DCD）→V（P³），最多 228 作业/5,088,000 更新；已登记队列在M2执行不完整后停止，后段未放行。公开catalog尚不存在，真实新数据未验收。M2 原核心 108×32k 与科学门禁不变；B90/C81 仍独立条件扩展，不自动插入新队列。

主线仍为 RGB–DSM 双向条件互补与退化/缺失分割，恢复旁支。T/V 是可能形成新问题的探索性方向，不因排入队列而视为取代主线，也不能把小网络开发结果视为超越现有方法。旧 Val2、Test6、held4、final 和新数据公开 test 均封存。只用物理 GPU0/1，中间数据有界内存处理；失败停止，不自动重跑或加种子。原始端点、轨迹和轻量证据在 `/home/jovyan/zzx` 的独立实验目录，重要结论同步本 GitHub 分支并回读。
