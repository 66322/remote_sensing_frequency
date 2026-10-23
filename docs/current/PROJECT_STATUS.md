# 当前状态：合并队列已登记，M2实际运行阶段待查（2026-10-23）

- 最新登记证据：2026-10-23 22:21:12+08:00，目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_combined_20261023T222112_2164225，控制器返回PID2166328。入口Done为正常退出；尚无控制器当前存活、M2目录或正式训练步数回执。
- 用户沿用remote_sensing，Torch已2.2.2+cu121、CUDA可用，三组combined目标检查通过。新建环境不是强制条件；旧xformers0.0.23.post1依赖冲突待实际日志确认，不能直接认定训练失败。
- 最后GPU0/1空闲观测21:52:05，H10080GB、ready=true；不能当实时状态。M2此前影像头预检和标签盲地理分折通过。
- 合并代码e65c6cb，M2固定ac325cd；M2 108×32k、J42/R18/T30/V30，总228作业/5,088,000更新和门禁不变。B90/C81未开放，公开catalog缺失，T/V尚无真实数据验收。
- 下一步只读查询现有队列状态、M2来源及日志，不再登记/单独开M2；失败无自动重试。详情及原始片段见[登记记录](../experiments/PHASE3_COMBINED_REGISTRATION_20261023.md)。
- 研究角色与保护范围不变：RGB–DSM主线、恢复旁支、连续地图维护为候选；旧Val2/Test6/held4/final和公开test封存。服务器用户执行、无SSH，原件均在/home/jovyan/zzx。
