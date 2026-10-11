# 新对话交接｜2026-10-11

权威源：GitHub `66322/remote_sensing_frequency`，分支 `rebuild-v1-protocol-20260915`。新对话先读 [START_HERE](../START_HERE.md)，依次读研究决定、HANDOFF、PROJECT_STATUS、NEXT_EXPERIMENT、[实验索引](../experiments/rebuild_v1/INDEX.md)，再核对[完整T报告](../experiments/POST_T_FULL_RESULTS_20261011.md)和[机制诊断协议](../protocols/POST_T_MECHANISM_GPU0_20261010.md)。本页仅为交接摘要；更新的原始服务器证据优先于本页旧时间状态。

## 已完成与证据边界

T0—T9 十组 fixed8000 技术完成；轻量原件含完成快照、逐组记录、执行代码/配置、上传清单、混淆矩阵及服务器大文件索引，存于 `records/research_post_s1_transfer_20261010T073327_2852696/completed_evidence_20261011T093311771593_3616761/`，原件提交 `379f301f255b9d2348cf11cad79e1374fedd1e7b`。整轮报告与离线审计在 GitHub；权重和大型预测数组留服务器对应目录，GitHub 的“记录完整”指可核对的轻量证据，不等于复制了全部大文件或重跑GPU。

Potsdam fit12→Val2 `3_11/5_10`、seed42、native512/stride256、NoBoundary `mIoU_fg5`：T7 RGB_U 83.876407%，比R0 85.001650%低1.125243个百分点。五个上下文匹配比较增益1.432—1.521个百分点且两tile同号；T7原科学门槛未通过。结论限于开发验证，不能扩展为双向/未知缺失泛化。研究主线仍为RGB–DSM双向条件互补与退化/缺失分割，任务驱动恢复为旁支。

## 当前队列：最后一次服务器观测

最后服务器只读查询（用户终端粘贴，未接收本轮指标原件）：QUERY_OBSERVED=2026-10-11T12:55:27.487901+08:00，queue LAST_OBSERVED=2026-10-11T12:55:15.361980+08:00，RUNNING_M333_context；controller PID3626108 LIVE=True，CPU=COMPLETE，仅GPU0。15/26整项COMPLETE、1项RUNNING、10项PENDING；前15个M已完成并退出，M333_context PID3718262 LIVE=True，phase=inference，tile=3_11，condition=rgb_lines64w8__aux_down4，windows=529/529，progress观测12:55:24.648101，elapsed=158.271144秒，optimizer_updates=0。单tile/条件窗口完成不等于整项完成。L_T0—L_T9尚未启动。这是最后观测，不代表实时状态。

前序已安全交接，原执行cd958925cb5d4292dd15802830e97493c9c67033与原目录research_post_t_mechanism_20261011T094823_3625851保持。所贴nohup日志确认依序完成15个M并启动M333_context，未见本次故障回报；没有精度、R0同源端点或训练轨迹原件，不能判机制成立。新增训练0。回报见[进度摘录](../../records/research_post_t_mechanism_20261011T094823_3625851/user_reported_progress_20261011T125527.json)。

目录 `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_t_mechanism_20261011T094823_3625851`。26项=M16模块/上下文组合＋L10现有4000步checkpoint推理，0新训练。已完成15个M的worker耗时704.836—760.205秒（约11.7—12.7分钟），替代未校准的2—4h估时。12:55时最后M约余9—10分钟；L每项只有4个tile单元，但加载/散列与汇总耗时未测，整队剩余仍须首个L实测校准。不得按条件数线性缩放承诺ETA。

只用物理GPU0；服务器由用户执行终端，无SSH；所有日志/代码快照/轻量归档在 `/home/jovyan/zzx` 对应实验目录。不开Test6、held4或最终集；不自动重跑失败配方、加种子或启用GPU1。可用队列目录内 `code/scripts/status_post_t_mechanism.py` 只读查询状态和nohup日志。

## 下一步与未完成的计划

先接收这26项的完成状态。技术完成后用已提交的 `scripts/upload_post_t_mechanism_records.py` 显式上传轻量原件，回读核验，再按预定M同源端点、模块配对和L的0→4000→8000轨迹复算。若技术失败，保留现有目录及日志定位，未经分析不重启。完成诊断后自动停止。

**下一轮真正训练尚未定型、未排队。** 依据诊断判别R0与私有分支差距：若专家包贡献且后段仍上涨，设计同预算的专家尾部适应；若接口/解码器解释差距，设计接口校准与简单控制；若模块交换失败，先检查兼容性。任何新训练要先冻结候选、匹配控制、主指标、保护门槛与停止条件，不能以扩大旧T预算挽救失败gate。新对话可在收到当前队列结果后制定并登记训练协议。
