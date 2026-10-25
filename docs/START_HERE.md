# 共享入口：M2 45/108，F0条件评价仍在途（2026-10-25）

长期必读：[仓库AGENTS](../AGENTS.md)、[稳定新对话入口](current/NEW_CHAT_HANDOFF.md)、[跨对话执行约定](protocols/EXECUTION_CONTRACT.md)。2026-10-24用户已将[启动交付与故障控制](protocols/STARTUP_DELIVERY_AND_FAILURE_CONTROL.md)确立为长期要求：真实包/分包布局验证、目标兼容路径、首败停止、未变检查复用。换对话不重新启动或补跑审计；日期入口只跳转当前文件。

机器重启或需用GPU0/1时先读[当前M2中断与释放协议](protocols/PHASE3_M2_INTERRUPTION_AND_GPU_RELEASE_20261025.md)：这版没有可恢复暂停/自动续跑，`last_resume.pth`不是已接入的恢复入口。终端断线不等于机器重启；确需立即释放两卡只能显式中止当前运行，先核验进程归属，再让原控制器清理自身子进程。此协议及工具发布未在服务器执行任何停止动作，不改变下方最后观测。

规划长期必读：[实验规划规范](protocols/EXPERIMENT_PLANNING_RULES.md)。探索默认单种子，必要重复通常先两个，三及以上说明两个不足的具体问题和额外成本；真实训练/评价吞吐须有证据。用户2026-10-25再次指出旧要求未落实，[本次复盘](experiments/PHASE3_PLANNING_POLICY_AUDIT_20261025.md)确认规则已存在但入口/计划落实遗漏。已补入口与准备表；尚未缩减服务器三种子队列或完成GPU profiling/提速，没有新增运行观测。

最新研究决定（2026-10-25）：采纳用户提出的[按阶段证据调整路线](protocols/ITERATIVE_RESEARCH_REVIEW_20261025.md)。每次新增完整配对结果先回答实验目的，再安排最小后续验证；原RGB–DSM线与地图线准备可并行。当前自动队列没有新增人工暂停点，未缩减、改排或启动新路线。

最新运行：[M2 45/108及F0评价续进度](experiments/PHASE3_M2_PROGRESS_20261025T221238.md)。最后服务器观测2026-10-25 22:12:38+08:00：M2 RUNNING，完成45/108、失败/阻断0；F0的36项训练齐全，条件评价已计399例，仍在`rgb_fault`阶段，M2无summary/gates。合并WAIT_M2；J/R/T/V未有阶段结果。这不是实时状态，继续既定队列，仅只读查询。F0三种子的clean局部结果见[20:35分析](experiments/PHASE3_M2_PROGRESS_AND_INTERIM_20261025T203508.md)，尚不能判融合或科学门禁。

最新研究方案：[连续建筑地图维护中的错误恢复与变化发现](experiments/INDEPENDENT_RESEARCH_ROUTE_20261023.md)。用户要求保留既有研究并寻找独立新路线；助手将旧地图候选细化为优先验证方向，尚未实现、运行或确认为新主线。少量核验纠正漏标保留备选，异步水域时间错配候选依据元数据审计降级。[前一轮期刊扫描](experiments/REMOTE_SENSING_JOURNAL_OPTIONS_20261022.md)保留为来源。

先读[研究决定](current/RESEARCH_DECISION.md)、[交接](current/HANDOFF.md)、[当前状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)，再读[合并队列执行合同](protocols/PHASE3_COMBINED_QUEUE_EXECUTION_20261022.md)、[M2完整协议](protocols/PHASE3_M2_ERROR_CORRESPONDENCE_20261015.md)和[M2执行修订](protocols/PHASE3_M2_EXECUTION_20261016.md)。[研究选择与跨领域方法草案](experiments/POST_M2_RESEARCH_OPTIONS_20261022.md)是候选来源，不等于各臂已得到正结果。

用户已提供登记、M2前置检查失败及随后原目录修复派发回执，最新回执确认修订两控制器存活且双GPU持续训练；此前要求将原 M2 与条件几何、表征对照以及新公开数据方向写成可一起启动的依赖队列。当前实现为 M2→J→R→T（3DCD）→V（P³），最多 228 作业/5,088,000 更新；旧队列因M2执行不完整停止；修订两目录M2已报45/108完成、F1 seed42 DClean/DShuffle仍在更新、失败0，J/R/T/V仍待M2完整性放行。公开数据就绪尚无验收回执，本次未复查catalog。M2 原核心 108×32k 与科学门禁不变；B90/C81 仍独立条件扩展，不自动插入新队列。

主线仍为 RGB–DSM 双向条件互补与退化/缺失分割，恢复旁支。T/V 是可能形成新问题的探索性方向，不因排入队列而视为取代主线，也不能把小网络开发结果视为超越现有方法。旧 Val2、Test6、held4、final 和新数据公开 test 均封存。只用物理 GPU0/1，中间数据有界内存处理；失败停止，不自动重跑或加种子。原始端点、轨迹和轻量证据在 `/home/jovyan/zzx` 的独立实验目录，重要结论同步本 GitHub 分支并回读。

范围与耗时：[228作业覆盖范围、同速情景及旧失败遗留](experiments/PHASE3_QUEUE_SCOPE_ETA_AND_REMAINS_20261024.md)。同速纯训练约72–75小时不等于完工ETA；新数据未就绪可无限等待。B/C及独立地图维护等候选未入队。

数据与保存位置：[新数据用途、两处服务器产物目录及保留/回收规则](experiments/PHASE3_DATA_AND_ARTIFACT_STORAGE_20261024.md)。M2/J/R沿用现有Potsdam，只有T/V需要额外公开数据；后段服务器publication不等于已自动上传GitHub。

启动复盘：[四类阻断、63条共性失败的调度放大及验证改进](experiments/PHASE3_STARTUP_POSTMORTEM_20261024.md)。主要问题是助手工程交付与真实执行链检查不足；本轮未操作服务器，不改变当前运行与研究决定。

只读查看：[当前队列进度、失败与各段结果](protocols/PHASE3_PROGRESS_AND_RESULTS.md)，复用服务器已有状态助手；按登记回执选择当前目录，不看旧失败目录，也不因查看重新启动。

最新指标记录：22:12只读表中的[F0三种子clean指标](experiments/PHASE3_M2_PROGRESS_20261025T221238.md)与20:35相同：DF在三seed均比D0低，且均低于DShuffle；F1仍缺D0配对。这些仅是同一外折的单模态信号，不代替条件补救/融合门禁；路线与队列未变。[只读口径](protocols/PHASE3_M2_INTERIM_RESULTS.md)。运行/GPU最后观测为22:12:38。
