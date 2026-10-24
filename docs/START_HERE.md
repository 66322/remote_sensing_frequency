# 共享入口：Python3.9 CPU模型预检已通过，正式工程重启未授权（2026-10-24）

最新执行记录：[Python3.9兼容预检通过](experiments/PHASE3_M2_PY39_IMPORT_FAILURE_20261024.md)。用户已回传CPU_PREFLIGHT_PASSED_NO_TRAINING_OR_RETRY / CPU_MODEL_IMPORT_AND_PUBLIC_WEIGHTS_PASSED。预检目录为原M2 repairs/dino_py39_preflight_20261024T090448_2718326（目录时间09:04:48，完成时刻未提供）。固定8680614脚本成功标志表明全部63条原始失败的导入前栈和无更新产物审计、DINO源Git对象/兼容副本核对、CPU构造模型与公共权重严格加载均通过，且原M2绑定/失败证据保持不变。尚未启动训练，也未验证CUDA前反传。 回执来源是用户终端成功标志；admission.json、cpu_model_passed.json、完整cpu_model.log原件尚未取回，不能称全量轻量原件已验收。进程/GPU最后带时间观测仍为2026-10-24 08:38:13，不是实时状态。CPU通过只验证修复方案可用于模型加载，不会修改旧M2实际启动路径或恢复控制器。 用户禁止自动重跑失败配方，下一步先明确是否允许一次纯工程修订后的正式重试，不自动启动。

最新研究方案：[连续建筑地图维护中的错误恢复与变化发现](experiments/INDEPENDENT_RESEARCH_ROUTE_20261023.md)。用户要求保留既有研究并寻找独立新路线；助手将旧地图候选细化为优先验证方向，尚未实现、运行或确认为新主线。少量核验纠正漏标保留备选，异步水域时间错配候选依据元数据审计降级。[前一轮期刊扫描](experiments/REMOTE_SENSING_JOURNAL_OPTIONS_20261022.md)保留为来源。

先读[研究决定](current/RESEARCH_DECISION.md)、[交接](current/HANDOFF.md)、[当前状态](current/PROJECT_STATUS.md)、[下一步](current/NEXT_EXPERIMENT.md)，再读[合并队列执行合同](protocols/PHASE3_COMBINED_QUEUE_EXECUTION_20261022.md)、[M2完整协议](protocols/PHASE3_M2_ERROR_CORRESPONDENCE_20261015.md)和[M2执行修订](protocols/PHASE3_M2_EXECUTION_20261016.md)。[研究选择与跨领域方法草案](experiments/POST_M2_RESEARCH_OPTIONS_20261022.md)是候选来源，不等于各臂已得到正结果。

用户已提供登记、M2前置检查失败及随后原目录修复派发回执，最新回执确认两控制器已停止；此前要求将原 M2 与条件几何、表征对照以及新公开数据方向写成可一起启动的依赖队列。当前实现为 M2→J→R→T（3DCD）→V（P³），最多 228 作业/5,088,000 更新；已登记队列在M2执行不完整后停止，后段未放行。公开catalog尚不存在，真实新数据未验收。M2 原核心 108×32k 与科学门禁不变；B90/C81 仍独立条件扩展，不自动插入新队列。

主线仍为 RGB–DSM 双向条件互补与退化/缺失分割，恢复旁支。T/V 是可能形成新问题的探索性方向，不因排入队列而视为取代主线，也不能把小网络开发结果视为超越现有方法。旧 Val2、Test6、held4、final 和新数据公开 test 均封存。只用物理 GPU0/1，中间数据有界内存处理；失败停止，不自动重跑或加种子。原始端点、轨迹和轻量证据在 `/home/jovyan/zzx` 的独立实验目录，重要结论同步本 GitHub 分支并回读。
