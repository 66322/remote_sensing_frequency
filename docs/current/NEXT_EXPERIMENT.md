# 下一步：在已登记09:28两目录修复model包路径后放行（2026-10-24）

1. 用户启动752d后已登记两revision_20261024T092814_2738345目录，但J头导入检查失败，尚无launch/release/jobs。新CPU模型、原16项和计划6项已通过。最后GPU/状态观测09:30:32，不是实时状态。
2. 依[新接续协议](../protocols/PHASE3_MODEL_NAMESPACE_CONTINUATION_20261024.md)执行repair_phase3_model_namespace.py --apply，固定补丁25b124a0cf69ececb6841b55ed90b19fae5b9a08。保留单次回执和旧错误，同目录接续，不重新bootstrap或memfd --apply。
3. 现场无启动/作业及原752d完整绑定必须通过；补丁8项、带明确model.__path__的原16项/合并11项全部通过，双方入口ready和GPU0/1复核后才放行。已有用户启动授权，不再重复确认。
4. 读取REGISTERED_REVISION_NAMESPACE_FIXED_LAUNCHED、新PID及原状态助手输出。首次M2_TRAIN ...1或progress step≥1确认训练更新；失败日志保留，不自动重试。
5. 修订源码/模型数学/种子/预算/科学门禁不改。额外验收两model_namespace_repair回执、补丁manifest/目标检查/launch及原752d runtime材料和训练轨迹；test封存、GPU0/1及有界内存保持。

## 独立新路线的下一步

用户已授权继续探索，助手优先推荐[连续建筑地图维护](../experiments/INDEPENDENT_RESEARCH_ROUTE_20261023.md)。先在SpaceNet7公开训练源中冻结有效月份、真实事件数、AOI隔离、当期地图监督和前缀评价合同；随后实施B1独立重建/B3递归模型及B2简单滤波/迟滞重置，量化自然错误持续、变化发现延迟和GT旧图诊断差距。拟议首阶段为三个地理开发划分、seed42、六个训练作业，具体清单与预算尚待数据验包后登记，不表示已入队。

若简单方法仍有残差，再做单步/rollout与普通递归/拟议维护的正交对照；若无残差则停止该机制。完整核验纠正漏标保留备选，异步水域时间错配暂缓。新路线无代码/数据运行回执，不能启动现成命令。

该研究不作为既定队列的新前置，不隐含暂停、改排或自动追加任务；服务器训练仍由用户执行，实施时另建合同与独立目录。新主线需明确决定并同步入口。
