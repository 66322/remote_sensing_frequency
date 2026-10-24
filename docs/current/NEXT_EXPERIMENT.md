# 下一步：M2原始失败取证，不重启（2026-10-24）

1. 最后观测08:38:13：M2 INCOMPLETE_NO_RETRY、合并STOPPED_NO_AUTOMATIC_RETRY，两PID均defunct，GPU0/1空闲；12/12输入准备及memfd/原16项检查通过。
2. 只读publication/summary.json的jobs_complete/expected、完整端点optimizer_updates、errors/failures，按不同error取最早failure完整traceback；结合jobs/*/progress.json与trajectory.jsonl确认真实更新情况。
3. 当前nohup尾部不含原始作业错误，不能据此归咎xFormers。G0关闭时性能门禁不能当作科学阴性；合并错误是下游停止，认证不可用为上传问题。
4. 不运行bootstrap或repair --apply、不改包或重跑失败配方，保留旧目录、源码和失败。若需新尝试，先明确新执行合同与失败保留。
5. 该轮publication未自动上传，后续取回轻量原件与轨迹再验收，不索取token。test封存、GPU0/1及有界内存不变。

## 独立新路线的下一步

用户已授权继续探索，助手优先推荐[连续建筑地图维护](../experiments/INDEPENDENT_RESEARCH_ROUTE_20261023.md)。先在SpaceNet7公开训练源中冻结有效月份、真实事件数、AOI隔离、当期地图监督和前缀评价合同；随后实施B1独立重建/B3递归模型及B2简单滤波/迟滞重置，量化自然错误持续、变化发现延迟和GT旧图诊断差距。拟议首阶段为三个地理开发划分、seed42、六个训练作业，具体清单与预算尚待数据验包后登记，不表示已入队。

若简单方法仍有残差，再做单步/rollout与普通递归/拟议维护的正交对照；若无残差则停止该机制。完整核验纠正漏标保留备选，异步水域时间错配暂缓。新路线无代码/数据运行回执，不能启动现成命令。

该研究不作为既定队列的新前置，不隐含暂停、改排或自动追加任务；服务器训练仍由用户执行，实施时另建合同与独立目录。新主线需明确决定并同步入口。
