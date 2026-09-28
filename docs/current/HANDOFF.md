# Current handoff — 2026-09-28, D18/D19 seed42 complete

## 当前事实与下一步

用户提供的服务器状态显示：2026-09-28 12:13:32 +08:00 队列 `QUEUE FINISHED`，
8/8 基础训练及评估完成、失败0；C4/C5因结构门槛未触发而按计划跳过。
用户提供的 `decision.json` 显示 P2 相对 P0/P1 中较强者综合 +1.0603 pp，
通过单seed预设筛选；C2、C3未通过。见
[D18/D19结果记录](../experiments/D18_D19_RESULTS_20260928.md)。

原始 `status.tsv`、`conditional_gate.json`、`decision.json` 和8份正式评估
`summary.json` 已由服务器上传至GitHub；离线重算审计通过，见
[`offline_audit.json`](../../records/rebuild_v1_d18_d19_compact_20260928/offline_audit.json)。
**立即下一步：**按同一冻结协议设计 P0/P1/P2 匹配seed17复验，不要只复验P2；
具体矩阵、判据、配对诊断和资源安排已写入
[D18匹配复验计划](../protocols/D18_MATCHED_SEED17_REPLICATION_PLAN_20260928.md)。
复验代码和队列尚未实现或启动。P2在DSM完全缺失时原模型比P0低约0.50 pp，
不能将辅助质量组的harm检查扩展成普遍缺失鲁棒性结论。
C2/C3本轮变体停止，C4/C5不启动。Test6继续冻结。服务器队列已结束，
不应按下文历史启动说明再次运行。

以下旧交接内容仅保留作时间线背景，不是当前启动指令。

最新用户要求：多方案单seed初筛；本批仅seed42，有信号后再选候选及必要对照补seed。
训练后必须自动重载、评估与汇总，物理GPU0/1共享任务，可跨一天继续。

## 立即下一步

代码已实现，本地9项CPU测试通过、2项CUDA检查待服务器；还核对官方DINOv2架构接口。
服务器尚未观测新队列启动。按 [执行说明](../protocols/D18_D19_EXECUTION_20260927.md)
启动 `scripts/run_rebuild_v1_d18_d19_queue.sh`，无需手动分别启动训练和评估。

8项基础：P0/P1/P2新预训练表示对照（8000步），C0/C1/C2/C3/CP融合对照（4000步）。
C4/C5仅在结构门槛通过后触发。全部seed42，无seed17任务。
DINOv2 ViT-S/14的代码commit、权重下载地址和配置已固定；后台创建独立d18_dino环境。
准备失败仅阻塞D18；D19可独立通过smoke后继续。每组所有独特分支短流程先验证。

每项训练后保存并重载最终权重，clean探针精确复算，然后Val2全图9条件＋2项固定新扰动，
记录CM、逐类/tile、harm/rescue、回退与FullGT边界计数。另复用D16旧权重做4项推理诊断。

队列记录：`records/rebuild_v1_d18_d19_queue_20260927/status.tsv`。
预训练准备日志：同目录 `D18_PREPARATION.log`。
最终判断：`records/rebuild_v1_d18_d19_20260927/decision.json`。
首次需要依赖和约84MB权重下载；启动前需要55GiB可用空间。新任务时长待服务器短流程实测。
Test6禁止；Potsdam Train16/Val2仍为探索协议。运行中不得修改已绑定配置/源码。

## 已完成的事实

最后观测D16/D17服务器完成时间：2026-09-27 22:53:47 +08:00，16正式任务、零失败。
原始归档e37d103；离线审计e4c3a09通过，A2/B1均未通过冻结双seed门槛，方案关闭。
见 [结果](../experiments/D16_D17_RESULTS_20260927.md)。不重新启动该队列。
D15仍支持特定RGB退化条件下的DSM互补；不能据D16/D17失败否定所有模态价值。

新骨干组是独立新起点，不能与旧R05继续训练直接作预算等价的机制比较。
CFI启发插入为分割适配，不声称复制原图像融合方法。容量对照参数接近但MAC不同。
点监督实例分割等交叉方向只准备数据条件，不是当前可执行任务。

[之前全部交接历史](../history/HANDOFF_20260927_before_D18_D19.md)只作背景，不据此重启旧实验。
