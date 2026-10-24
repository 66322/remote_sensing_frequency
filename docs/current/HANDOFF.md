# 当前交接：M2执行不完整停止，待原始作业异常（2026-10-24）

最后服务器观测2026-10-24 08:38:13+08:00：M2 PID2690788和合并PID2690789均Zs/defunct，GPU0/1均0MiB且无计算进程。M2于08:36:44.670358报告INCOMPLETE_NO_RETRY；合并于08:37:36.280856报告STOPPED_NO_AUTOMATIC_RETRY，原因M2 did not finish as server-checked。12/12输入准备于08:35:40.299463完成。此为最后观测，不是实时状态。

memfd实际libc后端探针及原16项检查已通过。G0完整性未通过时，其他性能门禁为False不能作研究阴性。当前未回传原始作业堆栈，具体错误、完成端点及失败前更新数未知；先读publication/summary.json、failures/*.json和jobs/*/progress.json。xFormers警告、合并下游异常和上传认证缺失均不能据此确定为训练根因。

详见[停止记录及用户片段](../experiments/PHASE3_M2_INCOMPLETE_20261024.md)。M2原目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m2_20261023T222114_2166330；合并原目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_combined_20261023T222112_2164225。原执行ac325cd/e65c6cb及接口修复b020000分别绑定。

立即下一步：用户只读summary、按不同error取最早failure完整traceback、检查job进度与轨迹。summary.optimizer_updates只计完整端点，不可当作所有尝试更新数。不要再次bootstrap或repair --apply，不改环境、不清理原失败、不重跑配方；现有失败作业使原登记期接纳条件不再成立。J/R/T/V未获得M2完整性放行。

原上传器报告既有认证不可用，publication原件未自动同步；GitHub目前只有用户回执及源码核对，未验收正式轻量原件/训练轨迹。上传修复与训练恢复分别处理，不索取token。

RGB–DSM条件互补/退化缺失分割仍为主线，恢复旁支，连续地图维护为独立候选。本次不改变研究决定；test封存、仅GPU0/1、有界内存及用户服务器执行无SSH不变。前一交接见[归档](../history/HANDOFF_20261024_BEFORE_M2_INCOMPLETE.md)。