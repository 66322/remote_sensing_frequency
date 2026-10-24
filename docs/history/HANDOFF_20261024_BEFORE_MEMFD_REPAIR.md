# 当前交接：合并队列已登记，先查M2运行状态（2026-10-23）

GitHub rebuild-v1-protocol-20260915为共享来源。RGB–DSM条件互补及退化/缺失分割为主线、恢复旁支；独立[连续地图维护候选](../experiments/INDEPENDENT_RESEARCH_ROUTE_20261023.md)未实现或训练，研究角色不改。

用户实际沿用remote_sensing，已升级Torch2.2.2+cu121，CUDA可用；无需再新建环境。旧xformers0.0.23.post1要求Torch2.1.2，与当前版本有依赖冲突，但尚无DINO实际前向失败证据，不盲目换包。

[登记回执](../experiments/PHASE3_COMBINED_REGISTRATION_20261023.md)：修复入口e65c6cb三组目标检查通过，2026-10-23 22:21:12+08:00登记：
`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_combined_20261023T222112_2164225`
控制器返回PID2166328；入口PID2164225显示Done属登记后正常退出。未接收当前queue_status.json、M2目录或训练日志，不称已开始训练、控制器实时存活或阶段完成。最后GPU0/1空闲观测仍21:52:05。

立即下一步：只读查询现有合并目录状态、控制器PID、m2_source.json/m2_bootstrap.log/nohup.log，以及唯一M2目录的状态/目标检查日志。不要重新登记合并队列、单独再开M2或重试失败科学配方。若失败先核查实际错误与是否发生正式更新，再制定修复。公开catalog仍缺，后段会WAIT_PUBLIC_DATA。

执行代码仍[e65c6cb](https://github.com/66322/remote_sensing_frequency/commit/e65c6cb0830985461b3cd30e2f43158dd3d858cb)，M2冻结ac325cdbb403ebb95b5eb0acbf17fffa5441dcfd；108×32k及总228作业/5,088,000更新、门禁、B/C未开放不变。[此前清单遗漏故障](../experiments/PHASE3_COMBINED_BOOTSTRAP_FIX_20261023.md)已修复，原包/日志保留；三组检查通过不等于实际模型CUDA或科学结果验收。

由用户服务器终端操作，无SSH，只用物理GPU0/1；旧Val2/Test6/held4/final及新数据公开test封存。原件在/home/jovyan/zzx，内存中间量用完回收。重要记录同步GitHub并回读；[登记前交接](../history/HANDOFF_20261023_BEFORE_COMBINED_REGISTRATION.md)归档。
