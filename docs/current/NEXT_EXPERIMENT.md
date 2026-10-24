# 下一步：用户执行一次已授权的工程修订启动（2026-10-24）

1. 用户明确“继续，把实验启动”，一次工程重试已授权，不再重复询问。使用[新执行协议](../protocols/PHASE3_ENGINEERING_RESTART_EXECUTION_20261024.md)的bootstrap_phase3_engineering_restart.py --apply，固定提交752d3835a18a15a04d83b1dcc1841bff98bf0b07。旧两失败目录保留，不用旧bootstrap/memfd --apply。
2. 启动器先核对旧63条零更新导入失败、CPU回执、原绑定/源码/权重、Torch2.2.2+cu121和GPU0/1；在新目录执行真实模型CPU加载、原16项和合并3套11项。所有检查通过且两个入口ready后才放行。
3. 查看新RESTART_LOG的ENGINEERING_RESTART_LAUNCHED和全局单次回执；用修订包status_phase3_engineering_restart.py查新run准备/进度/原始错误/PID/GPU。首次M2_TRAIN ... 1或progress step≥1才证明开始更新，启动器Done不等于训练结束。
4. 全局回执phase3_engineering_restart_20261024_once.json防止重复登记/派发。首个失败即停队，保留新旧错误，不删回执绕过，不自动重复失败作业。后段缺公开数据保持WAIT_PUBLIC_DATA。
5. 原228作业/5,088,000更新、种子、门禁和B/C封存不变。结束额外取回runtime_revision、CPU/launch/目标检查和原始训练轨迹再验收；test封存、GPU0/1及有界内存保持。

## 独立新路线的下一步

用户已授权继续探索，助手优先推荐[连续建筑地图维护](../experiments/INDEPENDENT_RESEARCH_ROUTE_20261023.md)。先在SpaceNet7公开训练源中冻结有效月份、真实事件数、AOI隔离、当期地图监督和前缀评价合同；随后实施B1独立重建/B3递归模型及B2简单滤波/迟滞重置，量化自然错误持续、变化发现延迟和GT旧图诊断差距。拟议首阶段为三个地理开发划分、seed42、六个训练作业，具体清单与预算尚待数据验包后登记，不表示已入队。

若简单方法仍有残差，再做单步/rollout与普通递归/拟议维护的正交对照；若无残差则停止该机制。完整核验纠正漏标保留备选，异步水域时间错配暂缓。新路线无代码/数据运行回执，不能启动现成命令。

该研究不作为既定队列的新前置，不隐含暂停、改排或自动追加任务；服务器训练仍由用户执行，实施时另建合同与独立目录。新主线需明确决定并同步入口。
