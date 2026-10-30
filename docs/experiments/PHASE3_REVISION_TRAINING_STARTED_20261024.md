# 修订M2双GPU真实训练已启动（2026-10-24）

状态：FORMAL_CUDA_TRAINING_UPDATES_OBSERVED_NO_COMPLETED_ENDPOINT。

最后服务器观测2026-10-24 09:54:39+08:00：M2为RUNNING，输入12/12已于09:49:45完成；GPU0的F0_s42_T3推进到2600/32000，GPU1的F0_s42_T1推进到2620/32000。两个控制器2754693/2754694存活，作业失败0、完成端点0；合并WAIT_M2为正常依赖等待。此为最后观测，不是实时状态。

来源为[用户粘贴终端原样副本](evidence/PHASE3_REVISION_TRAINING_STARTED_20261024.txt)。状态助手总时间09:54:39.817071，M2状态采样09:54:33.714745，GPU0/1进度分别采样09:54:38.458141与09:54:39.431504。不是服务器实时监控，也不替代全部原件验收。

## 当前执行证据

| 物理GPU | M2作业（F0，seed42） | 优化更新 | worker PID | GPU UUID |
|---|---|---:|---:|---|
| 0 | F0_s42_T3 | 2600/32000 | 2757402 | GPU-97a250ea-42ff-eb14-4ed5-8c50231e0baa |
| 1 | F0_s42_T1 | 2620/32000 | 2757403 | GPU-4b116760-e84c-2743-cee6-41cf76a01677 |

T1/T3均为M2开发交叉验证中的内层OOF RGB教师，不是队列后续3DCD高度变化T阶段。Fit12输入准备12/12于09:49:45.925189完成。日志包含两作业从1至2500的连续间隔更新，progress继续到2600/2620，已跨过首个CUDA优化更新。completed_trainings=0符合仍未达到32000预算；failed_or_blocked=0、job_failure_count=0。当前loss、梯度和激活均有数值，但不能由训练loss推断分割泛化或机制成立。

M2控制器PID2754693、合并PID2754694存活。合并WAIT_M2状态采样09:51:44.841983，引用M2采样09:51:32；约300秒刷新属于依赖等待，不要求与最新progress同秒。当前cpu_tasks=0、counted_cases=0、evaluation=null，count_workers=32只是配置，不代表正在执行32个计数任务。

nvidia-smi于09:54:39显示两卡各3737MiB总占用，计算进程各3728MiB，瞬时利用率各31%。这仅是采样，不用于判断完整吞吐瓶颈或修改批量/并行。ps ELAPSED异常，不作为时长依据。xFormers disabled/not available警告伴随实际训练更新，未阻断运行；无需据此改环境。

## 目录及来源

- M2：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m2_revision_20261024T092814_2738345。
- 合并：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_combined_revision_20261024T092814_2738345。
- 全局回执：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/phase3_engineering_restart_20261024_once.json，CONTROLLERS_LAUNCHED，09:46:44.633221。
- 工程基线752d3835a18a15a04d83b1dcc1841bff98bf0b07；额外包路径补丁25b124a0cf69ececb6841b55ed90b19fae5b9a08。M2科学来源ac325cdbb403ebb95b5eb0acbf17fffa5441dcfd、合并源e65c6cb0830985461b3cd30e2f43158dd3d858cb不变。
- [前阶段准备及目标检查回执](PHASE3_REVISION_PREPARING_20261024.md)：补丁8项、原M2全16项、合并11项通过。旧失败原件与两个旧run保留；本次没有再次登记/启动或新增训练。

## 下一步与证据边界

继续原队列，只读查询状态与8k/16k/24k/32k轨迹；下一关键证据是完整32k端点及其配置/checkpoint/原始整数计数绑定。当前仅属运行证据，尚无完成端点、validation性能或科学门禁通过结论。M2→J→R→T→V最多228作业/5,088,000更新，不因此次启动成功改研究角色或预算。

失败停止且不自动重跑/加seed，test及B/C封存，GPU0/1、有界内存、服务器由用户执行且无SSH保持。终止后另验收model_namespace_repair、补丁manifest/checks/repair_receipt/launch、752d runtime、CPU/target日志及全部轻量端点和轨迹；本次只有用户终端回执，未全量取回服务器原件。