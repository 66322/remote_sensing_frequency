# 共享入口：F16运行，零训练后继存活并正常等待

最后用户服务器查询：原配对2026-10-12T07:36:17.043567+08:00（queue观测07:36:11.273122），RUNNING/controller LIVE=True。CONTENT_PRE/H8/F8/R8/R16/H16共6/8 COMPLETE退出；F16 GPU1 RUNNING/LIVE=True，11680/16000、training；CONTENT_POST PENDING。训练更新回报67680/72000，不等于整轮评价完成比例，也不等于科学验收。R16 GPU0完成05:12:15.355236，H16 GPU1完成05:07:40.161959。原执行44e4df5afbaeb603e6441e7ef14ff09f228bc027和目录research_post_t_paired_v2_20261011T182543_3880702保持。

后继查询2026-10-12T07:36:16.999949+08:00（queue观测07:36:13.698186），WAITING_PREDECESSOR/controller LIVE=True，GPU_BLOCKED={0:false,1:false}，42项全PENDING、0运行/0完成/0技术失败。前序controller/worker存活、lock_free=False，所以未开始CPU影像扫描或GPU诊断。新目录research_structured_failure_v0_20261012T073410_81887、登记PID82130、执行f2ad4a9f38b32058f3855c2d18aa6a9b81df6cdd保持。以上为最后观测，不代表实时状态。

GPU0空闲由最后F16单任务及CONTENT_POST阶段依赖造成，不是卡被release或缺少已登记任务。R16完成后GPU0无本队列活动worker；H16较早结束的GPU1已接F16。F16技术完成后可用GPU0预计接CONTENT_POST，随后完整汇总/控制器与锁退出，后继才开始CPU准备；新后继clean两项及正式40任务按双卡共享队列派发。无需rejoin、重复enqueue、迁移F16或热改执行快照。

[配对07:36回报](../records/research_post_t_paired_v2_20261011T182543_3880702/user_reported_progress_20261012T073617.json)、[后继07:36回报](../records/research_structured_failure_v0_20261012T073410_81887/user_reported_progress_20261012T073616.json)。后继已经登记，不重复启动。预计前序交接粗观察窗口09:45—10:30（非承诺），其后先CPU mask可行性再GPU；详见[交接](current/HANDOFF.md)。

研究阶段仍为可行性探索与机制定位。主线RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复旁支。原六组配对、R16主候选与旧T7/U/E=False保持；当前loss不能用于比较训练效果。本轮精度、保护、R0差距、DSM内容原件均尚未接收独立验收，不因COMPLETE写科学成功。

后继为用户已授权的固定Phase1A零训练诊断：四系统×四族×20实现×两Val2，640缺失＋8clean＋6旧端点检查，42任务。主PE固定S1-0，CB用同权重M000 masked/context；GT只参与匹配/评价，mask实现不等于训练seed或独立地区。17项CPU合成检查通过，真实mask可行性与H100端点未验证；失败HOLD，不自动换条件/重试/20→40/Phase1B/Phase2或新训练。后继在前序技术完成退出后自动接续，不要求聊天端在线；科学结论仍待轻量原件回读。

用户需要某卡时才release，最新显式请求跨两队列生效，未完成推理case可在另一卡重做但0训练；已完成case复用。无全队24h截止，不自动恢复技术失败。服务器由用户执行、无SSH，记录和快照都在/home/jovyan/zzx对应实验目录；Test6/held4/final关闭。

读取顺序：[新对话交接](current/NEW_CHAT_HANDOFF_20261011.md)→[研究决定](current/RESEARCH_DECISION.md)→[HANDOFF](current/HANDOFF.md)→[PROJECT_STATUS](current/PROJECT_STATUS.md)→[NEXT_EXPERIMENT](current/NEXT_EXPERIMENT.md)→[实验索引](experiments/rebuild_v1/INDEX.md)。[原配对操作](protocols/POST_T_PAIRED_V2_EXECUTION_20261011.md)、[后继操作](protocols/STRUCTURED_FAILURE_V0_EXECUTION_20261011.md)。
