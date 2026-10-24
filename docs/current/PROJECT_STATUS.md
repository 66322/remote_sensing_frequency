# 当前状态：M2执行不完整，原队列已停止（2026-10-24）

- 最后服务器观测2026-10-24 08:38:13+08:00：M2 PID2690788和合并PID2690789均Zs/defunct，GPU0/1均0MiB且无计算进程。M2于08:36:44.670358报告INCOMPLETE_NO_RETRY；合并于08:37:36.280856报告STOPPED_NO_AUTOMATIC_RETRY，原因M2 did not finish as server-checked。12/12输入准备于08:35:40.299463完成。此为最后观测，不是实时状态。
- memfd实际libc后端探针及原16项检查已通过。G0完整性未通过时，其他性能门禁为False不能作研究阴性。当前未回传原始作业堆栈，具体错误、完成端点及失败前更新数未知；先读publication/summary.json、failures/*.json和jobs/*/progress.json。xFormers警告、合并下游异常和上传认证缺失均不能据此确定为训练根因。
- [停止取证记录](../experiments/PHASE3_M2_INCOMPLETE_20261024.md)。原M2目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m2_20261023T222114_2166330，原合并目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_combined_20261023T222112_2164225。
- 只读summary、failures和作业轨迹；不重新登记/修复--apply、不重跑或改包，J/R/T/V未放行。
- publication上传器提示既有认证不可用，原件未自动同步；当前是用户终端片段，不宣称完整原件或轨迹已验收。
- 原M2 ac325cd、合并e65c6cb及修复b020000分别绑定，科学合同/预算不变。
- 研究角色、test封存、GPU0/1、有界内存和用户执行边界不变；G0不通过时性能门禁不能作为科学阴性。