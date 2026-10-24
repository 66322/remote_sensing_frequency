# 共享入口：D30运行正常，最后确认20:56

## 最新实际存活检查：2026-10-03 20:56:13

用户只读查询确认D30控制器2349619 LIVE=True，两个重放worker存活，ACTIVE_RUNNING。queue最后观测20:56:08.886753+08:00；replay_G0 GPU0 6/24、replay_G1 GPU1 6/24，共12/48（25%），uniform模式已完成，expert0开始。四训练P/R/PR_area/PR_pixel仍PENDING，这是设计的重放阶段屏障。查询已正常，无新技术错误，不重复启动。

D28现在有直接状态观测：COMPLETE、controller.lock free；其state最后观测2026-10-03T19:27:53.313658+08:00。科学结果仍待上传/读取，不能从队列完成推出研究gate通过。以上是最后收到的状态，不宣称实时存活。[本次观测](../records/research_d30_loss_decomposition_20261003T205144_2349167/progress_observation_20261003T205613.json)。


## D30最新服务器观测：2026-10-03 20:52

用户已执行nohup启动，控制器PID2349619，CPU检查PASS；GPU0 replay_G0 PID2349792、GPU1 replay_G1 PID2349798已开始uniform固定混合评价。最后worker观测20:52:55.972803+08:00。D30已经完成自动接力并进入重放，四组新训练尚未观测开始；不是仍待启动，也不需要重复启动。当前时刻存活情况须用只读查询确认。

运行目录：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d30_loss_decomposition_20261003T205144_2349167。按冻结控制器执行链，开始worker表示D28终态、summary、锁释放与残留worker检查已通过；D28完整科学结果仍未读取，不能据此判断现象/gate。查询报错源于启动括号内cd不保留，当前shell在jovyan、相对plan路径不存在；错误只影响查询，不影响后台作业。查询改用绝对plan路径。[启动原件](../records/research_d30_loss_decomposition_20261003T205144_2349167/startup_observation.json)。


用户已执行固定commit 9db12dfb7ee85dff91dd6c246c7f161b60aca603，收到CPU检查PASS和两个重放worker日志；最后观测见上。四组训练尚未观测开始，D27失败门槛与D30原设计不变。

权威分支rebuild-v1-protocol-20260915。先读[研究决定](current/RESEARCH_DECISION.md)→[交接](current/HANDOFF.md)→[状态](current/PROJECT_STATUS.md)→[下一步](current/NEXT_EXPERIMENT.md)。

D27已完成并复核，当前四gate失败；D28最后收到18:34 RUNNING0/7，其后状态未知。新D30复用S0/S1，用48次checkpoint诊断和4组静态训练拆开损失目标。原D29未激活。仅GPU0/1 H10080GB、RAM/磁盘充足、batch16无累积、nohup、zzx对应目录，无资源探针。

[D30协议](protocols/D30_LOSS_DECOMPOSITION_AFTER_D28_20261003.md)、[实现与检查](experiments/D30_IMPLEMENTATION_20261003.md)、[D27原件复核](experiments/D27_FINAL_REVIEW_20261003.md)。已收到实际GPU0/1重放日志；NEXT内旧启动命令已执行，勿重复。[实施前入口归档](history/pre_D30_implementation_20261003/START_HERE.md)。
