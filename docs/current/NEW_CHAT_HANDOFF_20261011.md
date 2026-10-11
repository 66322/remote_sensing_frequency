# 新对话交接｜2026-10-11

权威源：GitHub `66322/remote_sensing_frequency`，分支 `rebuild-v1-protocol-20260915`。新对话先读 [START_HERE](../START_HERE.md)，依次读研究决定、HANDOFF、PROJECT_STATUS、NEXT_EXPERIMENT、[实验索引](../experiments/rebuild_v1/INDEX.md)，再核对[完整T报告](../experiments/POST_T_FULL_RESULTS_20261011.md)和[机制诊断协议](../protocols/POST_T_MECHANISM_GPU0_20261010.md)。本页仅为交接摘要；更新的原始服务器证据优先于本页旧时间状态。

## 已完成与证据边界

T0—T9 十组 fixed8000 技术完成；轻量原件含完成快照、逐组记录、执行代码/配置、上传清单、混淆矩阵及服务器大文件索引，存于 `records/research_post_s1_transfer_20261010T073327_2852696/completed_evidence_20261011T093311771593_3616761/`，原件提交 `379f301f255b9d2348cf11cad79e1374fedd1e7b`。整轮报告与离线审计在 GitHub；权重和大型预测数组留服务器对应目录，GitHub 的“记录完整”指可核对的轻量证据，不等于复制了全部大文件或重跑GPU。

Potsdam fit12→Val2 `3_11/5_10`、seed42、native512/stride256、NoBoundary `mIoU_fg5`：T7 RGB_U 83.876407%，比R0 85.001650%低1.125243个百分点。五个上下文匹配比较增益1.432—1.521个百分点且两tile同号；T7原科学门槛未通过。结论限于开发验证，不能扩展为双向/未知缺失泛化。研究主线仍为RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复为旁支。

## 当前队列：最后一次服务器观测

用户终端在2026-10-11 09:51:04+08:00查询：队列时间09:50:54，`RUNNING_M000_masked`，控制器PID3626108存活，CPU准备完成，GPU0 worker PID3626555正在推理；0/26整项完成。此为历史观测，**新对话必须重新查询，不能当作实时状态**。目录 `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_t_mechanism_20261011T094823_3625851`，执行提交 `cd958925cb5d4292dd15802830e97493c9c67033`。26项是M16模块/上下文组合加L10现有4000步checkpoint诊断，共0次新优化器更新；并非26组新训练。GitHub目前仅有本轮登记与09:51进度，无完成指标原件；不要重复登记或重启。

只用物理GPU0；服务器由用户执行终端，无SSH；所有日志/代码快照/轻量归档在 `/home/jovyan/zzx` 对应实验目录。不开Test6、held4或最终集；不自动重跑失败配方、加种子或启用GPU1。可用队列目录内 `code/scripts/status_post_t_mechanism.py` 只读查询状态和nohup日志。

## 下一步与未完成的计划

先接收这26项的完成状态。技术完成后用已提交的 `scripts/upload_post_t_mechanism_records.py` 显式上传轻量原件，回读核验，再按预定M同源端点、模块配对和L的0→4000→8000轨迹复算。若技术失败，保留现有目录及日志定位，未经分析不重启。完成诊断后自动停止。

**下一轮真正训练尚未定型、未排队。** 依据诊断判别R0与私有分支差距：若专家包贡献且后段仍上涨，设计同预算的专家尾部适应；若接口/解码器解释差距，设计接口校准与简单控制；若模块交换失败，先检查兼容性。任何新训练要先冻结候选、匹配控制、主指标、保护门槛与停止条件，不能以扩大旧T预算挽救失败gate。新对话可在收到当前队列结果后制定并登记训练协议。
