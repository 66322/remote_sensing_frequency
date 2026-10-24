# 当前状态：原M2登记期memfd检查失败，兼容修复待应用（2026-10-24）

- 最后服务器观测2026-10-23 22:31:10+08:00：GPU0/1 H10080GB空闲；合并控制器2166328为defunct，STOPPED_NO_AUTOMATIC_RETRY。不是当前实时状态。
- 原合并目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_combined_20261023T222112_2164225；原M2目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m2_20261023T222114_2166330。M2目标16项15通过，唯一失败为os.memfd_create缺失；发生于训练控制器启动前，无正式训练回执。
- 当前remote_sensing已Torch2.2.2+cu121；原M2环境函数已禁用xformers，本次不改装环境。
- 兼容修复代码[b020000](https://github.com/66322/remote_sensing_frequency/commit/b0200004f30a8d55eef2049ecdfb30ef97f3d034)及[执行说明](../experiments/PHASE3_M2_MEMFD_REPAIR_20261024.md)已准备。9项本地兼容/接纳检查通过；实际服务器memfd与原16项待用户执行。失败不放宽门禁、不落盘回退。
- 只允许在原目录确认无训练后显式接续；原M2 ac325cd、合并e65c6cb源码和绑定保持不变，修复SHA另记runtime_repair.json；旧失败证据保留。
- M2 108×32k、J42/R18/T30/V30，总228作业/5,088,000更新，门禁及B/C未开放不变。公开catalog缺失，T/V真实数据尚未验收。
- 研究角色不变；旧Val2/Test6/held4/final及新数据公开test封存。服务器用户执行、无SSH，仅GPU0/1，原件与修复都在/home/jovyan/zzx。
