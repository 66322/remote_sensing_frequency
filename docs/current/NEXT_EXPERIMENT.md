# 下一步：继续M2，等首折36作业后的完整面板评价（2026-10-24）

已采纳[长期启动规则](../protocols/STARTUP_DELIVERY_AND_FAILURE_CONTROL.md)及[稳定新对话入口](NEW_CHAT_HANDOFF.md)；不因本次记录更新重新预检或启动。

1. 最后服务器观测2026-10-24 22:49:33+08:00：M2 RUNNING，控制器报告完成17/108训练作业、失败/阻断0，19个作业有progress；GPU0 F0_s17_DShuffle为16600/32000，GPU1 F0_s17_DEntropy为11420/32000。两控制器及两GPU worker存活，合并WAIT_M2。当前完整故障面板counted_cases=0、evaluation=null，尚无M2阶段summary。这是最后观测，不是实时状态或完整科学验收。
2. 当前只读运行records/phase3_engineering_restart_package_752d3835a18a15a04d83b1dcc1841bff98bf0b07/scripts/status_phase3_engineering_restart.py --tail 20，结合progress更新时间、失败记录和控制器状态；跨阶段结果见[查看指南](../protocols/PHASE3_PROGRESS_AND_RESULTS.md)。
3. 用户需要看已有指标时，按[中间评价只读汇总](../protocols/PHASE3_M2_INTERIM_RESULTS.md)读取固定32k、四tile齐全的clean单模态结果；尚无实际分数回传，不提前宣布哪臂有效，不额外训练/推理。
4. 下一里程碑是首折全部36作业完成且mask就绪后出现完整Evaluation和案例计数；年龄轨迹另存，不进counted_cases。最终M2汇总仍等108作业和全部计数finalize，不能把缺summary或当前CPU无在途任务判为失败。
5. 发现新FAILED/STOPPED或进度异常先保存首栈并诊断，不自动重跑。既有目录、失败前史和单次回执保留，不bootstrap、repair --apply、改环境、重启或扩seed/配方。本轮仅只读接续。
6. 本次两加权臂实测约0.35秒/步，不继续按首批教师0.1秒/步估整队列；剩余1.5/2小时仅两在途作业纯优化。后续按正式作业类型与完整评估自然日志更新ETA，不另起探针或改预算。
7. 阶段完成后核对配置/checkpoint/SHA、原始整数计数、配对样本流、训练轨迹、752d/25b124修订材料和轻量上传；再解释科学gates。J/R/T/V仍按原依赖合同，B/C和test封存，公开数据就绪等待不自动跳过。详见[最新回执](../experiments/PHASE3_M2_PROGRESS_20261024T224933.md)。

## 独立新路线的下一步

用户已授权继续探索，助手优先推荐[连续建筑地图维护](../experiments/INDEPENDENT_RESEARCH_ROUTE_20261023.md)。先在SpaceNet7公开训练源中冻结有效月份、真实事件数、AOI隔离、当期地图监督和前缀评价合同；随后实施B1独立重建/B3递归模型及B2简单滤波/迟滞重置，量化自然错误持续、变化发现延迟和GT旧图诊断差距。拟议首阶段为三个地理开发划分、seed42、六个训练作业，具体清单与预算尚待数据验包后登记，不表示已入队。

若简单方法仍有残差，再做单步/rollout与普通递归/拟议维护的正交对照；若无残差则停止该机制。完整核验纠正漏标保留备选，异步水域时间错配暂缓。新路线无代码/数据运行回执，不能启动现成命令。

该研究不作为既定队列的新前置，不隐含暂停、改排或自动追加任务；服务器训练仍由用户执行，实施时另建合同与独立目录。新主线需明确决定并同步入口。
