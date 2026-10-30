# 修订队列接续成功，进入Fit12输入准备（2026-10-24）

状态：CONTROLLERS_RELEASED_INPUT_PREPARING_FIRST_UPDATE_UNCONFIRMED。

最后服务器观测2026-10-24 09:48:32+08:00：路径补丁已完成全部目标检查并于09:46:44放行两个控制器；M2 PID2754693为Rs、合并PID2754694为Ss，均存活。M2 LAUNCHED_PREPARING，输入准备7/12（tile6_9，09:48:31），无progress、无作业失败；合并WAIT_M2。GPU0/1均0MiB/无计算进程，符合尚在CPU准备的阶段。不是当前实时状态，尚无首个优化更新或CUDA训练成功证据。

来源为[用户粘贴终端原样副本](evidence/PHASE3_REVISION_PREPARING_20261024.txt)。附件包含前次09:30失败及随后09:46–09:48成功输出，按最新带时间段判定。未取回服务器全部轻量原件，不把终端标志替代全部归档验收。

已通过：新补丁接纳/路径8项、原M2全16项（Linux匿名FD实际传递）、合并三套6+2+3共11项，日志逐套CHECK_PASSED。REGISTERED_REVISION_NAMESPACE_FIXED_LAUNCHED observed_at09:46:44.633221，两个入口ready后放行。memfd为libc.memfd_create，anonymous/cloexec/mapping_roundtrip均真，disk_fallback=false；model搜索路径明确为两处已校验源码。

## 执行与目录绑定

- M2：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m2_revision_20261024T092814_2738345。
- 合并：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_combined_revision_20261024T092814_2738345。
- 基线修订752d3835a18a15a04d83b1dcc1841bff98bf0b07；包路径补丁25b124a0cf69ececb6841b55ed90b19fae5b9a08，科学来源M2 ac325cd/合并e65c6cb保持。
- 新补丁启动日志records/phase3_model_namespace_20261024T094625.log；补丁快照/目标日志在M2 repairs/model_namespace_25b124a0cf69ececb6841b55ed90b19fae5b9a08。
- 全局phase3_engineering_restart_20261024_once.json为CONTROLLERS_LAUNCHED，包含两个PID、明确目录和previous_failure_receipt；旧失败已归档保留，不再混在当前启动error字段。

## 当前判断与下一步

这是工程目标检查及控制器/准备进度的运行证据，不是论文训练/性能结论。M2 prepare先核对原输入SHA并加载12个Fit12 tile/边界统计，完成后与旧input_index完全比较，再创建GPU worker。7/12且最后一tile时间持续推进，不是仅凭GPU空闲判断卡死。合并WAIT_M2是依赖等待，状态约300秒刷新，不代表M2停止。

下一步仅只读状态助手，观察准备达到12/12后RUNNING及jobs/*/progress.json step≥1/M2_TRAIN ...1。不要再次修复、bootstrap、删除回执或重启两个控制器。若出现FAILED/STOPPED/异常栈，保留新证据再诊断，不自动重跑失败配方。

ps的ELAPSED值异常，不用该值计算运行时长；本次只据STAT、队列时间戳和输入进展判定存活/准备。GPU实测只对应09:48:32，不能倒推后续状态。

科学预算228作业/5,088,000更新、种子、门禁及B/C封存不变；GPU0/1、test封存、有界内存及用户服务器执行无SSH保持。结束另验收两个model_namespace_repair、752d runtime_revision、CPU/目标日志/launch材料、模型端点和原始计数/训练轨迹；目前尚无这些完整原件验收结论。

## 后续记录

本页保存09:48准备阶段的历史观测。09:54:39已确认双GPU分别2600/2620次实际更新，见[后续训练启动证据](PHASE3_REVISION_TRAINING_STARTED_20261024.md)。本页等待首更的下一步已完成，勿重复启动。
