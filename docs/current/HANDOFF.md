# Current handoff — 2026-09-28, D20 Stage A server probe complete

**最新可执行：**训练区 P2 20步吞吐测量已于16:23:08 +08:00通过，服务器精简
记录归档`abe10e4`。稳态每步中位0.222秒，8,000步P2纯训练约0.49小时。
已据此冻结[三组seed42正式同域开发协议及队列](../protocols/D20_VAIHINGEN_SEED42_FORMAL_20260928.md)，
待服务器运行。开发17块均来自同一镶嵌图；不自动补seed17，不作独立最终确认。

**最新交接：**Vaihingen P0/P1/P2 一步短流程已于16:15:54 +08:00全部通过，
三组训练、保存重载及512开发裁块评估成功；服务器归档`8401bcd`。
见[结果](../experiments/D20_VAIHINGEN_SMOKE_RESULTS_20260928.md)。单步指标不用于选模。
下一项可执行的是[只读训练区的20步P2吞吐测量](../protocols/D20_VAIHINGEN_FIT_BUDGET_PROBE_20260928.md)，
测完才冻结正式三组预算；US3D传输/条款继续独立处理。

## 当前事实与下一步

D20 Stage A 已在服务器执行 `6c7c0d1`：本地 DFC19 三元组为0；官方 Track-1
torrent 元数据可达并确认 RGB/Truth 两个所需包；GRSS/DataPort 代理403。
当前阻塞是实际数据传输及使用条件，尚未完成数据准入或GPU队列。
[实测与 Vaihingen 可用角色](D20_STAGE_A_SOURCE_ACCEPTANCE_20260928.md)；
[GitHub 紧凑记录](../../records/rebuild_v1_d20_source_acceptance_compact_20260928/user_reported_stage_a.json)。
Vaihingen 已有部分可用三元组，可作开发实验；其旧实验曝光及同一镶嵌图邻近关系
限制了独立最终确认结论，TOP 输入是近红外/红/绿，需单独冻结通道协议。
[Vaihingen 内容检查](D20_VAIHINGEN_CONTENT_AUDIT_20260928.md)修正版已于服务器通过：
17/17同域开发候选块的三类影像尺寸一致、DSM样本有限、FullGT标签颜色样本均
属于既有调色板；原始结果归档`66ac041`。地理坐标对齐仍未知，标签为采样检查。
首次路径错误记录在`5299318`。Vaihingen 的
[三组一步匹配短流程](../protocols/D20_VAIHINGEN_MATCHED_SMOKE_20260928.md)
已通过服务器CUDA验证，TOP按近红外/红/绿原顺序、旧训练12块与新开发17块冻结；
它没有自动启动正式训练。US3D独立来源传输和条款问题单独继续。

服务器 D18 seed17 队列于 2026-09-28 14:52:05 +08:00 完成：P0/P1/P2
三组短流程、正式训练、评估、配对分析及精简归档均成功。服务器原始六份
seed42/17 评估摘要已在 GitHub 提交 `705d8d2`；本机离线审计 `PASS`，
见 [结果报告](../experiments/D18_REPLICATION_RESULTS_20260928.md)及
[`offline_audit.json`](../../records/rebuild_v1_d18_replication_compact_20260928/offline_audit.json)。
P2相对同seed最强P0/P1的综合增益分别为+1.0603／+0.9229 pp，
两个seed各自通过五项预设门槛。P2原模型完整DSM缺失时分别比P0
低0.4986／0.4103 pp；显式切换P0只验证availability策略。

**立即下一步：**先确认可用的独立场景来源、既往曝光、RGB/高度/语义标签配对、
类别映射和使用条件；依据
[独立来源决策](INDEPENDENT_SOURCE_DECISION_20260923.md)
评估US3D，若不具备条件再评估Houston。具体顺序见
[D20阶段计划](../protocols/D20_INDEPENDENT_SOURCE_AND_MATCHED_BASELINES_20260928.md)：
来源准入→冻结fit/dev/final→P0/P1/P2 seed42三组→开发门槛通过后再补seed17三组→
另定可靠性干预。最终区域保留到全部方法与对照冻结后统一评价。
Stage A 来源与传输审计脚本已执行；D20同域正式开发队列现已实现，服务器运行待验证。
不重启D18/D19或seed17队列。
Val2只有两个场景且已反复使用，两种子通过仍是开发证据；Test6保持冻结。

以下旧交接内容仅保留作时间线背景，**不是当前启动指令**。

最新用户要求：多方案单seed初筛；本批仅seed42，有信号后再选候选及必要对照补seed。
训练后必须自动重载、评估与汇总，物理GPU0/1共享任务，可跨一天继续。

## 历史：旧D18/D19队列启动说明（已完成，禁止重启）

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
