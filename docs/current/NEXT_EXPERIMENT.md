# 下一步：只读核验已派发控制器及首次训练状态（2026-10-24）

1. 用户修复日志phase3_memfd_repair_20261024T083216.log已出现ORIGINAL_M2_TARGET_CHECKS_PASSED和EXISTING_M2_MEMFD_REPAIR_LAUNCHED；M2 PID2690788、合并PID2690789已派发。启动器Done为父进程退出，不等于训练结束。
2. 原目录只读查询：date、两个PID的ps、M2 queue_status.json/preparation_progress.json/gpu0.json/gpu1.json/controller_failure.json/memfd_wrapper_failure.json、M2 nohup.log及新repair/combined_nohup.log；GPU0/1状态共同核对。不要再次登记、运行修复--apply或清理日志。
3. 准备阶段先哈希输入并载入12个Fit12 tile，随后启动GPU worker；暂时GPU空闲需结合准备进度、进程和异常判断。合并WAIT_M2为正常等待M2完成，约300秒刷新，不代表M2未启动。
4. 服务器原始target_checks.log与runtime_repair/launch回执尚待取回；终端通过标志不能替代全部原件核验。失败停止，不自动重试；只读新错误再决定工程修复。
5. 科学门禁、test封存、仅GPU0/1、有界内存、无新增seed/失败配方重跑不变。完成后核验端点与训练轨迹，额外同步修复包轻量证据。

## 独立新路线的下一步

用户已授权继续探索，助手优先推荐[连续建筑地图维护](../experiments/INDEPENDENT_RESEARCH_ROUTE_20261023.md)。先在SpaceNet7公开训练源中冻结有效月份、真实事件数、AOI隔离、当期地图监督和前缀评价合同；随后实施B1独立重建/B3递归模型及B2简单滤波/迟滞重置，量化自然错误持续、变化发现延迟和GT旧图诊断差距。拟议首阶段为三个地理开发划分、seed42、六个训练作业，具体清单与预算尚待数据验包后登记，不表示已入队。

若简单方法仍有残差，再做单步/rollout与普通递归/拟议维护的正交对照；若无残差则停止该机制。完整核验纠正漏标保留备选，异步水域时间错配暂缓。新路线无代码/数据运行回执，不能启动现成命令。

该研究不作为既定队列的新前置，不隐含暂停、改排或自动追加任务；服务器训练仍由用户执行，实施时另建合同与独立目录。新主线需明确决定并同步入口。
