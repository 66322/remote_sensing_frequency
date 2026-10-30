# 历史：完成回执接收前的交接

仅供历史，返回[当前交接](../current/HANDOFF.md)。

# 当前交接：Full原队列保持，空间读出改为自动接续（2026-10-30）

2026-10-30 20:41:08用户回执确认：两空间头已于20:39:39完成全部阶段，各2000步且learned=true；DINOv2/DINOv3训练循环约22.78/28.50秒。接续进程已退出，自动上传因EXISTING_AUTH_UNAVAILABLE待补传，no_recompute=true。当前只读汇总现成Full和空间结果，不再执行任何start/bootstrap/repair。Full正常收尾及释放GPU可由接续成功推断，但11项是否全合格仍待其完成摘要；空间校准/outer分数尚未收到。按[NEXT](NEXT_EXPERIMENT.md)只读汇总现成结果；Full本身继续只读跟进，不再运行旧bootstrap、A0 continuation或repair。助手无SSH，发布代码不是服务器已执行。

## 最后真实进度及绑定

- ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro。物理GPU0/1两张H100；不触碰GPU2–7或未知进程。
- 原A0 run：records/post_m2_a0_ipcfix_20261030；科学c22a046407daf42064cbb161429f2648c9b86d66、IPC执行修复d15f34e8d53f935aa17542123c2227fab14cb810。19:01两边各2k及全部评价完成。内校准+1.6257pp、outer开发−0.6527pp，[完整结果](../experiments/POST_M2_A0_RESULTS_AND_REVIEW_20261030.md)。原校准READY保留，A1/A2仍未入队，空间2×2保留。
- 旧A0 records/post_m2_a0_capability_20261029的长AF_UNIX目录故障已处理：确认归属16个进程全部停止，SIGKILL列表空、剩余列表空；失败原件未改。未观察到成功旧更新不等于精确零更新。不再启动旧入口。
- Full code：execution/post_m2_multiroute_v2_20261030_r1，冻结d15；run：records/post_m2_multiroute_v2_20261030_r1，入口最后PID2517098。禁止热改/重启，不能因终端在pointcept环境就换包或改当前进程。
- 最后实际回执2026-10-30 19:38:20+08：GPU0/PID2518876 Q2/3000；GPU1/PID2518877 G1/1100。两100步窗口约2.238/2.954秒，数据等待0.149/0.159ms、占步时<1%，只代表这两窗口。[原始观察](../../records/post_m2_multiroute_v2_20261030_r1/progress_observations/20261030T193820/observation.json)。
- B0/B1/Q1/S1已返回8k训练循环；至少36,100次Full优化为源码/调度下界，S1资格及完整外层分数尚未收到。余Q3/G2/G3/S2/S3由现有控制器按真实前置合格派发或阻断，不能保证全都执行。

## 新接续入口

代码固定提交5f2958ae8b7d3ac79901eb0261239d89e82b461e；[发布回执](../../records/post_m2_a_spatial_followup_20261030_release/publication_receipt.json)，[执行说明](../experiments/POST_M2_A_SPATIAL_FOLLOWUP_20261030.md)。新run为records/post_m2_a_spatial_followup_20261030_r1，与Full独立，原DINOv3路径从修复A0的train_started来源读取，不靠当前shell变量。

一次start后台注册。等待Full正常train_complete、原controller锁释放及GPU0/1空闲，不等GitHub上传。等待只用CPU/小回执，不占GPU。使用已有remote_sensing绝对Python。新常驻双进程复用骨干和拟合数组，训练结束释放拟合数组，再校准→原screen→条件outer。各2k/seed42，只有新空间头各4步粗测；不重复原A0、原骨干profile、模型下载或权重哈希。

Full工程失败/无正常回执退出、已有旧空间尝试或未知进程占GPU时不派发；本入口失败不自动重试，只停止自身拥有的进程组。科学资格INVALID保存，不能说一般机制无效。新程序已有目标两空间头各2000步及全部阶段完成回执；原始计数和缓存复用回执待接收。

GPU先释放，再导出压缩小证据与summary/gates并沿已有认证上传；失败只续传，不重算。两空间端点只列路径/大小并保留服务器。C/P/E/F、A1/A2、频率仍未排队，seed预算96k不扩。Val2/Test6/held4/final封存。

M2清理仍暂缓，最后确认18端点、无最终成功删除回执；J工程停止，均不重启。跨电脑以本分支为准，不因换电脑重验已通过绑定。当前文档更正前版本存[历史目录](../history/20261030_before_a_spatial_followup/)。
