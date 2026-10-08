# 下一步：启动已冻结Post-S1 GPU0队列，回报登记与状态

用户已授权按GPU0[规划](../protocols/POST_S1_SUPPORT_GPU0_PLAN_20261008.md)实施。[冻结执行包](../protocols/POST_S1_SUPPORT_EXECUTION_20261008.md)已实现，READY_NOT_REGISTERED：D0复用/拼接→D1四权重四策略→P十组→E六条件→独立汇总。P7固定候选、S1-0基座SHA、新8000×10/seed42、fixed8000主比较、原科学门槛保持。CPU合成检查22项及12Python语法通过；没有真实服务器权重/backbone/GPU复跑，服务器登记前再跑同包检查。

下一步：用户从本次执行提交提取scripts/enqueue_post_s1_support.py到zzx bootstrap，使用原plan绑定的Python运行--root ROOT --commit固定提交。入口先核原队列与源码/权重SHA/锁，再CPU检查、幂等登记并nohup。重复调用只回报已有队列；失败/部分目录先诊断，不另登记第二条。新目录records/research_post_s1_support_<timestamp>_<pid>，只读status_post_s1_support.py，完成/失败后显式upload_post_s1_support_records.py。

仅物理GPU0，physical_gpus=[0]、CUDA_VISIBLE_DEVICES=0、单worker FIFO，所有诊断/训练/推理/恢复均不得使用GPU1。nohup、全部记录/快照/cache/temporary/上传worktree在zzx对应新目录；用户终端执行，无SSH，无Test6/独立final/held4、追加seed或失败配方自动重跑。旧双卡入口不适用于本轮。

FIFO次序D1→P6→P7→P8→P9→P4→P5→P2→P3→P0→P1→E；CPU D0在D1前。D1 64逻辑U单元（16复用、48新增tile推理），E 144新增tile推理。总10新训练/80000更新，Q四组不在可运行任务列表。CPU掩码/预测整理期间GPU空闲属正常准备态，必须看带时间status，不从空闲推断中断。

固定8000主比较、4000仅诊断；ordinary32和fixed22＋U，全部原计数/逐tile/权重/源码/输入/mask绑定保存。P7须RGB_U对基座≥2pp、对P6/P8/P9≥.3pp且两tile正、对R0≥−.2pp；clean/fullmissing保护−.1、最差primary tile−.2、DSM_U−.1；E六条件保护及两个clean-DSM新形状≥.5pp/两tile正。精确非支持保护是工程属性，不能单独作创新，E仍非独立测试集。

可行性探索，主线仍RGB–DSM条件互补与退化/缺失分割，任务恢复旁支。N3当前区域增量不足，S1 RGB局部+4.102047pp但aux_shift8/3_11−0.391546pp保护失败，旧gate维持False；本轮研究缺失支持与参数隔离，不自动升级单向收益为双向贡献。N5/N2/C旧去留保持，R1/N4/R2不激活。

最后服务器查询仍为2026-10-08T22:11:10.555448+08:00；原queue最后观测06:37:48.607436，N3_S1_COMPLETE_AWAITING_REVIEW，九组COMPLETE/8000，查询时controller/worker LIVE=False。本次没有新的服务器登记、PID或GPU进度回报。
