# 共享入口：修订M2双GPU真实训练更新已确认（2026-10-24）

最新运行记录：[双GPU训练启动证据](experiments/PHASE3_REVISION_TRAINING_STARTED_20261024.md)。最后服务器观测2026-10-24 09:54:39+08:00：M2为RUNNING，输入12/12已于09:49:45完成；GPU0的F0_s42_T3推进到2600/32000，GPU1的F0_s42_T1推进到2620/32000。两个控制器2754693/2754694存活，作业失败0、完成端点0；合并WAIT_M2为正常依赖等待。此为最后观测，不是实时状态。 已跨过导入、准备与首个CUDA优化更新；当前继续原队列，仅只读查询，不重复修复或启动。

最新研究方案：[连续建筑地图维护中的错误恢复与变化发现](experiments/INDEPENDENT_RESEARCH_ROUTE_20261023.md)。用户要求保留既有研究并寻找独立新路线；助手将旧地图候选细化为优先验证方向，尚未实现、运行或确认为新主线。少量核验纠正漏标保留备选，异步水域时间错配候选依据元数据审计降级。[前一轮期刊扫描](experiments/REMOTE_SENSING_JOURNAL_OPTIONS_20261022.md)保留为来源。

先读[研究决定](current/RESEARCH_DECISION.md)、[交接](current/HANDOFF.md)、[当前状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)，再读[合并队列执行合同](protocols/PHASE3_COMBINED_QUEUE_EXECUTION_20261022.md)、[M2完整协议](protocols/PHASE3_M2_ERROR_CORRESPONDENCE_20261015.md)和[M2执行修订](protocols/PHASE3_M2_EXECUTION_20261016.md)。[研究选择与跨领域方法草案](experiments/POST_M2_RESEARCH_OPTIONS_20261022.md)是候选来源，不等于各臂已得到正结果。

用户已提供登记、M2前置检查失败及随后原目录修复派发回执，最新回执确认修订两控制器存活且双GPU持续训练；此前要求将原 M2 与条件几何、表征对照以及新公开数据方向写成可一起启动的依赖队列。当前实现为 M2→J→R→T（3DCD）→V（P³），最多 228 作业/5,088,000 更新；旧队列因M2执行不完整停止；修订两目录经路径接续已放行、完成12/12准备并确认双GPU各达到至少2600次训练更新，J/R/T/V仍待M2完整性放行。公开catalog尚不存在，真实新数据未验收。M2 原核心 108×32k 与科学门禁不变；B90/C81 仍独立条件扩展，不自动插入新队列。

主线仍为 RGB–DSM 双向条件互补与退化/缺失分割，恢复旁支。T/V 是可能形成新问题的探索性方向，不因排入队列而视为取代主线，也不能把小网络开发结果视为超越现有方法。旧 Val2、Test6、held4、final 和新数据公开 test 均封存。只用物理 GPU0/1，中间数据有界内存处理；失败停止，不自动重跑或加种子。原始端点、轨迹和轻量证据在 `/home/jovyan/zzx` 的独立实验目录，重要结论同步本 GitHub 分支并回读。

范围与耗时：[228作业覆盖范围、同速情景及旧失败遗留](experiments/PHASE3_QUEUE_SCOPE_ETA_AND_REMAINS_20261024.md)。同速纯训练约72–75小时不等于完工ETA；新数据未就绪可无限等待。B/C及独立地图维护等候选未入队。

数据与保存位置：[新数据用途、两处服务器产物目录及保留/回收规则](experiments/PHASE3_DATA_AND_ARTIFACT_STORAGE_20261024.md)。M2/J/R沿用现有Potsdam，只有T/V需要额外公开数据；后段服务器publication不等于已自动上传GitHub。
