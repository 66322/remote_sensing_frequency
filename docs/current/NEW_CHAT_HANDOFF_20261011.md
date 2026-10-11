# 新对话交接：双卡队列已登记，首项进度待查询

权威共享源：66322/remote_sensing_frequency，rebuild-v1-protocol-20260915；本地仅工作副本。

最后服务器只读查询2026-10-11T18:35:43.956508+08:00：queue LAST_OBSERVED=18:35:35.350928，RUNNING，controller LIVE=True。CONTENT_PRE在GPU0 RUNNING/LIVE=True、0优化器更新；progress观测18:35:21.772826、elapsed566.033441秒，phase=M000_context/S、tile5_10、rgb_lines64w8__clean、windows529/529。529/529只代表当前tile/条件窗口，整项前测尚未完成。H8/F8/R8/R16/H16/F16及CONTENT_POST均PENDING，当前0/8整项完成、1运行、7待办，新增训练0。此为最后观测，不是实时查询。

原目录research_post_t_paired_v2_20261011T182543_3880702、执行44e4df5afbaeb603e6441e7ef14ff09f228bc027、controller登记PID3881013保持。前测单队列任务形成阶段屏障，因此此刻GPU1没有可派发实验；CONTENT_PRE完整后自动进入最多两卡训练。代码默认两卡启用，用户尚未发出release；GPU1实际硬件可用性尚无nvidia-smi原件。继续原队列、稍后只读查询，不重复登记/启动，不为检测停卡而release。查询证据：[进度回报](../../records/research_post_t_paired_v2_20261011T182543_3880702/user_reported_progress_20261011T183543.json)。

研究阶段为可行性探索与机制定位。主线仍RGB–DSM双向条件互补与退化/缺失分割，恢复为旁支。已验线索限Potsdam fit12→重复Val2 3_11/5_10、seed42、已知RGB局部缺失；DSM_U为保护结果。旧T7/U/E=False保持，不后验换M303/T5，不声称双向、未知故障或独立泛化。

用户已要求具体安排并执行准备；最新明确授权GPU0＋GPU1、预留一天以上、24h后未完成继续。需要哪张卡时，该卡任务保存后退出；未完成部分与待运行任务自动在另一张卡排队续跑。被释放卡保持停用，显式rejoin后才参与派发。此授权覆盖旧“只GPU0”资源限制，研究配方、seed与门槛不变。

六组F/H/R×8k/16k、72000优化器调用，主候选R16；前后各24内容诊断case、0更新。阶段顺序CONTENT_PRE→[H8,F8,R8]→[R16,H16,F16]→CONTENT_POST；方括号内为共享队列优先顺序，每张可用卡一个worker，已保存的续跑优先。8k三组技术完整且batch配对通过后才进16k，不按8k分数筛选。

H训练私有RGB net.rgb与decoder[:-1]；R另开末4编码块；最终分类器decoder[-1]冻结。6组统一S1-0初值、独立新优化器，同组真实batch散列配对；8k/16k为预算×日程比较。容量差异及DSM内容破坏的解释边界保留。X8/X16不可自动派发，DSM镜像/新频域/恢复扩张/多seed均未采纳。

代码已实现：六份完整配置、真实梯度/冻结契约、逐step输入散列、每500状态/每4000绑定验证、固定终点与次要选模、C端点复现、双卡控制及原件上传。本地CPU合成检查通过，包含单卡释放后跨卡续跑调度与优化器/RNG恢复；不等于真实H100、实权重或跨CUDA逐位一致验收。旧26项只查完成/进程/绑定，不重复登记或训练。

[执行与操作说明](../protocols/POST_T_PAIRED_V2_EXECUTION_20261011.md)、[配对细则](../protocols/POST_T_PAIRED_ADAPTATION_BUDGET_20261011.md)、[研究排期](../protocols/POST_T_RESEARCH_SEQUENCE_20261011.md)、[机制结果](../experiments/POST_T_MECHANISM_RESULTS_20261011.md)、[实现验收](../../records/post_t_paired_v2_implementation_20261011/verification.json)、[此前交接归档](../history/POST_T_PAIRED_V2_PRE_EXECUTION_HANDOFF_20261011.md)。

立即下一步：保留正在运行的CONTENT_PRE；稍后查询原目录manage status与nohup，确认前测完整并进入H8/F8双卡派发。无需重新登记，不主动release/rejoin，不测试占卡退出。已有队列继续执行。无SSH，所有记录在/home/jovyan/zzx对应目录，Test6/held4/final关闭。

预留一天以上，无全队24h截止；完成固定任务后自动停。单臂累计活跃时间保护仍为8k 12h、16k 24h、内容批次4h，排队/主动释放等待不计。OOM/绑定/非有限/技术失败HOLD，保留现场且不自动重试；主动释放属于同一任务续跑。完整后显式上传轻量原件，再独立复算全部配对、轨迹、内容与保护并制定后继，不能把本地检查写为实验已验证。
