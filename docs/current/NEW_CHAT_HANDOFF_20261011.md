# 新对话交接：双卡队列已登记，首项进度待查询

权威共享源：66322/remote_sensing_frequency，rebuild-v1-protocol-20260915；本地仅工作副本。

旧队列最后完整查询仍为2026-10-11T13:48:26.474610+08:00，26/26已完成退出、0新训练，原件57ef5ad9已验收。

用户终端已回报PAIRED_QUEUE_REGISTERED：目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_t_paired_v2_20261011T182543_3880702，controller PID3881013，执行44e4df5afbaeb603e6441e7ef14ff09f228bc027，GPU=0,1，6训练/72000计划步/48内容case。目录18:25:43与nohup18:25:52.609577来自命名时间，并非queue observed_at；尚无status/controller存活/worker进度原件。当前REGISTERED_PROGRESS_NOT_YET_QUERIED。用户感觉只GPU0活跃，未提供nvidia-smi输出，不能据此确认具体阶段。

已核对执行代码：CONTENT_PRE为单个串行诊断任务，完成前所有训练阻塞；这一阶段只用一张卡，完成后H8/F8可分别在GPU0/1派发。两卡默认均启用，仅显式release（或技术HOLD）才退出任务，不提前停用卡。用户本次仅启动/watch，无release命令。先查询原队列，不重复enqueue或启动worker。登记证据见[用户回报](../../records/research_post_t_paired_v2_20261011T182543_3880702/user_reported_registration_20261011.json)。

研究阶段为可行性探索与机制定位。主线仍RGB–DSM双向条件互补与退化/缺失分割，恢复为旁支。已验线索限Potsdam fit12→重复Val2 3_11/5_10、seed42、已知RGB局部缺失；DSM_U为保护结果。旧T7/U/E=False保持，不后验换M303/T5，不声称双向、未知故障或独立泛化。

用户已要求具体安排并执行准备；最新明确授权GPU0＋GPU1、预留一天以上、24h后未完成继续。需要哪张卡时，该卡任务保存后退出；未完成部分与待运行任务自动在另一张卡排队续跑。被释放卡保持停用，显式rejoin后才参与派发。此授权覆盖旧“只GPU0”资源限制，研究配方、seed与门槛不变。

六组F/H/R×8k/16k、72000优化器调用，主候选R16；前后各24内容诊断case、0更新。阶段顺序CONTENT_PRE→[H8,F8,R8]→[R16,H16,F16]→CONTENT_POST；方括号内为共享队列优先顺序，每张可用卡一个worker，已保存的续跑优先。8k三组技术完整且batch配对通过后才进16k，不按8k分数筛选。

H训练私有RGB net.rgb与decoder[:-1]；R另开末4编码块；最终分类器decoder[-1]冻结。6组统一S1-0初值、独立新优化器，同组真实batch散列配对；8k/16k为预算×日程比较。容量差异及DSM内容破坏的解释边界保留。X8/X16不可自动派发，DSM镜像/新频域/恢复扩张/多seed均未采纳。

代码已实现：六份完整配置、真实梯度/冻结契约、逐step输入散列、每500状态/每4000绑定验证、固定终点与次要选模、C端点复现、双卡控制及原件上传。本地CPU合成检查通过，包含单卡释放后跨卡续跑调度与优化器/RNG恢复；不等于真实H100、实权重或跨CUDA逐位一致验收。旧26项只查完成/进程/绑定，不重复登记或训练。

[执行与操作说明](../protocols/POST_T_PAIRED_V2_EXECUTION_20261011.md)、[配对细则](../protocols/POST_T_PAIRED_ADAPTATION_BUDGET_20261011.md)、[研究排期](../protocols/POST_T_RESEARCH_SEQUENCE_20261011.md)、[机制结果](../experiments/POST_T_MECHANISM_RESULTS_20261011.md)、[实现验收](../../records/post_t_paired_v2_implementation_20261011/verification.json)、[此前交接归档](../history/POST_T_PAIRED_V2_PRE_EXECUTION_HANDOFF_20261011.md)。

立即下一步：查询已登记原目录manage status、nohup与当前worker日志，确认CONTENT_PRE/训练阶段及两卡派发。无需重新登记，不主动release/rejoin，不测试占卡退出。已有队列继续执行。无SSH，所有记录在/home/jovyan/zzx对应目录，Test6/held4/final关闭。

预留一天以上，无全队24h截止；完成固定任务后自动停。单臂累计活跃时间保护仍为8k 12h、16k 24h、内容批次4h，排队/主动释放等待不计。OOM/绑定/非有限/技术失败HOLD，保留现场且不自动重试；主动释放属于同一任务续跑。完整后显式上传轻量原件，再独立复算全部配对、轨迹、内容与保护并制定后继，不能把本地检查写为实验已验证。
