# 当前状态：D30重放12/48，D28 COMPLETE

## 最新实际存活检查：2026-10-03 20:56:13

用户只读查询确认D30控制器2349619 LIVE=True，两个重放worker存活，ACTIVE_RUNNING。queue最后观测20:56:08.886753+08:00；replay_G0 GPU0 6/24、replay_G1 GPU1 6/24，共12/48（25%），uniform模式已完成，expert0开始。四训练P/R/PR_area/PR_pixel仍PENDING，这是设计的重放阶段屏障。查询已正常，无新技术错误，不重复启动。

D28现在有直接状态观测：COMPLETE、controller.lock free；其state最后观测2026-10-03T19:27:53.313658+08:00。科学结果仍待上传/读取，不能从队列完成推出研究gate通过。以上是最后收到的状态，不宣称实时存活。[本次观测](../../records/research_d30_loss_decomposition_20261003T205144_2349167/progress_observation_20261003T205613.json)。


## D30最新服务器观测：2026-10-03 20:52

用户已执行nohup启动，控制器PID2349619，CPU检查PASS；GPU0 replay_G0 PID2349792、GPU1 replay_G1 PID2349798已开始uniform固定混合评价。最后worker观测20:52:55.972803+08:00。D30已经完成自动接力并进入重放，四组新训练尚未观测开始；不是仍待启动，也不需要重复启动。当前时刻存活情况须用只读查询确认。

运行目录：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d30_loss_decomposition_20261003T205144_2349167。按冻结控制器执行链，开始worker表示D28终态、summary、锁释放与残留worker检查已通过；D28完整科学结果仍未读取，不能据此判断现象/gate。查询报错源于启动括号内cd不保留，当前shell在jovyan、相对plan路径不存在；错误只影响查询，不影响后台作业。查询改用绝对plan路径。[启动原件](../../records/research_d30_loss_decomposition_20261003T205144_2349167/startup_observation.json)。


研究仍处可行性探索：RGB–DSM双方条件互补、任一模态退化/缺失可靠分割。频率和专家是候选解法，任务驱动恢复仍旁支，未决定转向或冻结论文贡献。

D27修复轮已完成10/10并上传cedbc594d4e438d3c220ee80d3e82f563a8c2ae3，500份tile原件复核支持当前四gate失败。保护/恢复使综合下降约1.8pp；DSM独有正确保留增加伴随更大的RGB正确计数损失；动态/局部/类别增量不足。known missing回退成立但不代表未知失效鲁棒性。证据限开发Val2/seed42，不能扩大为研究问题失败。

D28最后收到的服务器观测为2026-10-03T18:34:10.615615+08:00：RUNNING、0/7，RGB_anchor在GPU0、DSM_anchor在GPU1。尚未收到更晚状态，不能推定当前完成。既定七模型、238次tile评价继续，禁止重复启动。

| 阶段 | 最后观测/记录 | 科学与执行状态 |
|---|---|---|
| D26 | 2026-10-03 04:04 COMPLETE9/9 | 已复核，原主候选门槛未过，保留普通融合 |
| 原D27 | 2026-10-03 04:12，全部step0失败 | 技术失败，无科学结果，目录保留 |
| D27 repair | 2026-10-03 18:22 COMPLETE10/10；原件已上传复核 | 当前四科学gate失败，known missing回退维持 |
| D28 | 最后state观测2026-10-03 19:27 COMPLETE；20:56确认锁已释放 | 队列完成，完整科学结果待上传读取 |
| D29 | 条件计划 | 未实现/未排队，旧前提未过 |
| D30 | 2026-10-03 20:56存活确认，RUNNING replay | GPU0/1各6/24，总12/48；四组训练PENDING，CPU PASS |

[D27复核](../experiments/D27_FINAL_REVIEW_20261003.md)、[D30计划](../protocols/D30_LOSS_DECOMPOSITION_AFTER_D28_20261003.md)、[当前交接](HANDOFF.md)。服务器由用户终端操作，无SSH。仅GPU0/1，两卡H10080GB；RAM/硬盘充足，无资源审计。物理batch16无累积；长任务nohup，所有快照/临时/缓存/日志在/home/jovyan/zzx相应实验目录。Test6禁读，开发Val2非独立final。GitHub此分支为共享权威，权重/预测本体服务器保留索引。

[旧状态全文](../history/pre_D30_plan_20261003/PROJECT_STATUS.md)已归档；旧“只收到启动、结果待核对”不再作当前事实。

## D30实施更新

用户已执行固定commit 9db12dfb7ee85dff91dd6c246c7f161b60aca603，收到CPU检查PASS和两个重放worker日志；最后观测见上。四组训练尚未观测开始，D27失败门槛与D30原设计不变。

[启动/查询](NEXT_EXPERIMENT.md)、[实现检查](../experiments/D30_IMPLEMENTATION_20261003.md)。
