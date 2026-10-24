# 下一步：应用原目录memfd兼容修复，再核验首次训练状态（2026-10-24）

1. 已有用户回执定位为M2登记期唯一memfd测试失败；不重复登记combined/M2，不安装新环境或重装xformers。最后观测22:31:10（2026-10-23），原控制器停止、GPU0/1空闲；实际资源仍由执行时检查。
2. 按[修复协议](../experiments/PHASE3_M2_MEMFD_REPAIR_20261024.md)使用完整提交b0200004f30a8d55eef2049ecdfb30ef97f3d034，对原合并目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_combined_20261023T222112_2164225及M2目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m2_20261023T222114_2166330执行repair_phase3_m2_memfd.py --apply一次。
3. 脚本必须确认无launch/训练作业痕迹、原绑定/代码完整、原失败匹配、两控制器锁可获取及GPU0/1可用；真实内核匿名memfd探针和原16项全部通过才接回控制器。发现已有训练/其他失败则停止，不自动重试或另选目录。
4. 查看新修复日志的ORIGINAL_M2_TARGET_CHECKS_PASSED与EXISTING_M2_MEMFD_REPAIR_LAUNCHED、新PID及原M2 queue_status.json/nohup.log。旧target_checks.log和合并旧nohup.log保留失败记录，新检查/监督器日志在repairs/memfd_<修复SHA>。
5. 完成后核验原件、计数和轨迹，另上传runtime_repair.json及repair清单/接纳/检查/launch证据；原上传器不保证自动包含这些文件。科学门禁、test保护、失败不重跑、缺公开数据后段WAIT_PUBLIC_DATA均不变。

## 独立新路线的下一步

用户已授权继续探索，助手优先推荐[连续建筑地图维护](../experiments/INDEPENDENT_RESEARCH_ROUTE_20261023.md)。先在SpaceNet7公开训练源中冻结有效月份、真实事件数、AOI隔离、当期地图监督和前缀评价合同；随后实施B1独立重建/B3递归模型及B2简单滤波/迟滞重置，量化自然错误持续、变化发现延迟和GT旧图诊断差距。拟议首阶段为三个地理开发划分、seed42、六个训练作业，具体清单与预算尚待数据验包后登记，不表示已入队。

若简单方法仍有残差，再做单步/rollout与普通递归/拟议维护的正交对照；若无残差则停止该机制。完整核验纠正漏标保留备选，异步水域时间错配暂缓。新路线无代码/数据运行回执，不能启动现成命令。

该研究不作为既定队列的新前置，不隐含暂停、改排或自动追加任务；服务器训练仍由用户执行，实施时另建合同与独立目录。新主线需明确决定并同步入口。
