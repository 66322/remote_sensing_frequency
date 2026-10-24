# M2执行不完整：停止并取证（2026-10-24）

状态：INCOMPLETE_NO_RETRY_ROOT_CAUSE_PY39_IMPORT_IDENTIFIED。

最后服务器观测2026-10-24 08:38:13+08:00：M2 PID2690788和合并PID2690789均Zs/defunct，GPU0/1均0MiB且无计算进程。M2于08:36:44.670358报告INCOMPLETE_NO_RETRY；合并于08:37:36.280856报告STOPPED_NO_AUTOMATIC_RETRY，原因M2 did not finish as server-checked。12/12输入准备于08:35:40.299463完成。此为最后观测，不是实时状态。

memfd实际libc后端探针及原16项检查已通过。G0完整性未通过时，其他性能门禁为False不能作研究阴性。当前未回传原始作业堆栈，具体错误、完成端点及失败前更新数未知；先读publication/summary.json、failures/*.json和jobs/*/progress.json。xFormers警告、合并下游异常和上传认证缺失均不能据此确定为训练根因。

[用户终端粘贴副本](evidence/PHASE3_M2_INCOMPLETE_TERMINAL_20261024.txt)含查询时间、ps、两个queue_status、准备进度、nohup末尾和GPU状态；不是服务器原件全量归档。ps的ELAPSED异常，不用该值估算运行时长。

## 执行与证据边界

M2原目录 /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m2_20261023T222114_2166330；合并原目录 /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_combined_20261023T222112_2164225。M2冻结ac325cdbb403ebb95b5eb0acbf17fffa5441dcfd、合并e65c6cb0830985461b3cd30e2f43158dd3d858cb、接口修复b0200004f30a8d55eef2049ecdfb30ef97f3d034分别绑定，沿用remote_sensing/Torch2.2.2+cu121。

代码核对：control_phase3_m2将作业FAILED事件收进failures列表，失败依赖写skipped，最终phase3_m2_analysis.finalize只有端点、配对初始化/样本流、计数、轨迹均齐全且无失败才写COMPLETE_SERVER_CHECKED，否则INCOMPLETE_NO_RETRY。因此M2_FINISHED仅代表控制器终结，不能当作成功验收。原任务异常保存在failures/<task_id>.json，含error/traceback/observed_at，不保证打印到nohup末尾。

summary.optimizer_updates只累加完整端点，不等于所有尝试的真实更新数。先取summary中的jobs_complete、errors、failures，再按错误类别读最早原始failure，结合jobs进度/轨迹确定失败前是否更新。未取到错误前不猜测修补，不把不完整数据当作路线失败。

M2_RESULTS_READY_UPLOAD_PENDING_EXISTING_AUTH_UNAVAILABLE仅表明publication未自动上传，不是训练根因证明。当前GitHub只同步用户片段和代码核对，未验收summary、原始训练轨迹或模型原件。只恢复证据上传不代表恢复训练，不索取token。

## 当前动作

只读取证，不重新bootstrap、执行修复--apply或重跑失败配方。原目录已有作业/失败/publication，先前登记期无作业修复的接纳条件不再成立。若需修订代码后试跑，先明确新执行合同与旧失败保留，不能将清理目录当作新作业。J/R/T/V未通过M2完整性放行。

[此前memfd检查记录](PHASE3_M2_MEMFD_REPAIR_20261024.md)仍保留，目标检查成功不保证训练执行链完整。研究角色、test封存、仅GPU0/1、有界内存及用户执行无SSH约束不变。本轮无新启动、改包或重试。

## 后续根因已定位

用户2026-10-24回传summary/失败节选（此次查询未带时间）：M2 INCOMPLETE_NO_RETRY，0/108完整端点、0评价案例、0个progress.json；63个failure均报unsupported operand type(s) for |: type and NoneType。展示的完整堆栈位于Python3.9加载DINOv2 attention.py的float | None注解，在make_model导入阶段，尚未进入该作业优化器构造或训练循环。全部63个原始堆栈及无更新产物仍由预检逐项核验。

上文根因待取证为08:38:13时的证据边界，已由[Python3.9导入故障记录](PHASE3_M2_PY39_IMPORT_FAILURE_20261024.md)更新。CPU兼容副本预检已实现、本地7项通过，服务器未执行；旧失败仍保留，不自动重跑。