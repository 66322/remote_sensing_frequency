# 当前交接：TS再次失败，TF已训练；先读TS错误并保留TF

2026-10-01最新用户回传：日志显示TS启动后TECHNICAL_FAILURE，GPU1 TF PID815379在elapsed_minutes=2.0打印D23_GATE_TRAIN TF 1。没有独立观测墙钟，不作为实时存活保证。GPU0空闲是TS失败所致；TF最后观测已开始训练，不应为诊断TS停止TF。

代码已确认prepare_resume_job在旧失败目录没有checkpoint时仍提前创建target，而worker新训练拒绝已有output目录，构成确定的接续缺陷。此缺陷已修复：仅有checkpoint才创建目标目录用于复制，否则把未创建路径交给worker。11项本地针对性检查通过，包括失败无checkpoint的新目录条件。该缺陷是否就是本次TS实际异常，仍需读取TS本次log_path中的末尾错误；不要把推断当作服务器错误原件。

立即下一步仅读取queue_status中TS日志末尾，同时保留TF继续执行；暂不重复运行--resume-queue（TF工作进程仍可能存活）。上一空闲等待修复保留；模型/engine/runtime lock不变。修复代码已发布，服务器尚未执行此版。TSF/T0完成保留，八组仍未完成。

历史交接背景（旧状态不覆盖上述最新观测）：

## 最新接续观测（2026-10-01用户回传）

用户已执行3c2d8e5d465272ba257b006e5b8f2926a2bca2f7的nohup接续。controller PID815309；日志为本次正式目录/nohup_handover_20261001T175826_811992.log。文件名含启动标识17:58:26，本条没有独立观测墙钟，不能作为实时存活保证。

最后回传：GPU0显存0MiB、利用率0、无compute PID，随后TS进程PID815349创建；GPU1相同空闲读数已第一次确认，第二次确认及TF进程启动尚未回传。等待是修复后的组间切换检查，间隔2秒、最长90秒；不是新的资源预算审计。未取得TS/TF训练step，不写成训练推进或完成。

立即动作改为沿此后台任务继续；不要再次启动。需要核对时只tail上述日志，预期出现GPU1 TF进程创建。TSF/T0既有完成结果保留，六组补齐后上传并分析。以下为原失败和修复背景，不能按其“待接续”状态重复启动。

更新2026-10-01；共享分支rebuild-v1-protocol-20260915。原证据提交9a70648affe105367e1b6e42ac4919f66140d7aa；目录records/research_d23_b_formal_20261001T152548_658274/evidence_20261001T175246424862_812335。最后队列观测2026-10-01T16:35:53.227191+08:00为TECHNICAL_FAILURE；用户随后报告两卡闲置，不是助手实时服务器观测。

TSF于16:34:33、T0于16:35:51由controller记录COMPLETE，日志均有4000步和两tile×14条件评价完成。TS启动退出码2，唯一错误为requested physical GPU is busy; no job is interrupted；没有正式训练/评价完成记录。TF/TCAP/TSF_CE/shuffleS/shuffleF未启动，screen_result不存在。当前是2/8完成，不能写成全队列完成、机制成立或全部验收通过。

研究仍是频率＋语义可靠性对RGB–DSM退化/缺失融合的可行性探索；C1旁支、部分解冻强基线；角色和冻结阈值不变。Test6禁读，Potsdam Val2为开发证据。

本轮修复仅修改controller：每次启动前等待目标GPU与锁定UUID一致，连续两次满足原空闲条件，最长90秒；显示显存、利用率和compute PID。现有日志不能区分历史采样延迟与真实占用，不能声称确定根因。等待超时保留错误，不终止别人任务。保留被跳过的完成组元数据/日志链接；模型、训练入口、engine、lifecycle、probe、runtime lock均未修改。10项本地模拟检查通过，服务器修复执行尚未观测。

下一步：用新controller在原目录nohup --resume-queue接续，仅补TS/TF/TCAP/TSF_CE/TSF_shuffleS/TSF_shuffleF六组，跳过TSF/T0，原失败日志/结果保留。GPU0/1两张H10080GB、主机内存/磁盘充足，所有记录在zzx对应目录。无需再跑smoke/预算。每组4000步、专家micro8、gate16、单backward及各项风险/机制门槛继续沿冻结协议。完成后前台上传轻量原件，再进行八组比较。
