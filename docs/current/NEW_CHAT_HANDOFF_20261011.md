# 新对话交接：Phase2设计已具体化，尚未启动（2026-10-13）

2026-10-13用户要求结合Phase1.5结果和所附审查规划下一轮，GPU0/1、至少一天可用窗口、未完继续，并行分析和大内存驻留。方案状态 DESIGN_SPECIFIED / EXECUTION_NOT_IMPLEMENTED_NOT_REGISTERED：当前没有新运行ID/PID、训练或队列。

[Phase2完整设计](../protocols/PHASE_2_MATCHED_COMPLEMENTARITY_20261013.md)替代此前同日草案：先A_RGB/A_DSM公共DINOv2-S/14、DSM固定复制3通道、同初始化/fit12/batch stream，各16k；固定16k端点后冻结专家，B0静态/B2同容量信号消融各8k；仅在匹配互补C、可观测偏好L、静态后剩余差距及保护通过时运行B1/B3各8k。核心4训练48k，最多6训练64k，无自动residual旁支。

重要修正：已知单模态缺失ROI硬回退只有一个合法专家，不能用于证明动态路由改善；reported missing与unreported local zero/down4分面板，后者用于动态可靠性门禁，均做RGB/DSM镜像。静态与动态头不joint训练专家，比较相同冻结端点与公共流；8k为16k轨迹中间点，不是独立8k日程。

本次补充审计旧Phase1.5的720个S1非clean回执，全部逐窗口dsm_only logits identity=True；内部fallback检验已存在，不重复GPU计算。旧DSM-only对RGB损坏的自身damage恒0，不能拿它与S1约21pp比较证明fallback。[发现登记](../experiments/FINDINGS_REGISTRY_PHASE2_20261013.md)、[回执](../../records/phase2_design_20261013/internal_dsm_identity_audit.json)。这是已上传运行证据的复核，无GPU复跑；精确拼接后身份/KL=0是同logits推论，不伪称新增测量。

资源预留24–48h并可继续，无24h强停，不为填时长扩样。两卡训练/共享推理队列，CPU统计随case流水；分析初选16进程并受真实quota/affinity限制，数值库各1线程；训练每卡8线程crop/prefetch8；hot cache初始256GiB且≤实际可用内存50%，紧凑FP32冻结logits估算93.75GiB（8000步双专家），保持等价后复用。用户最新free显示1.9TiB available，未带时钟且不是容器配额；显存/核数仍需启动只读探针。首200训练步和首8完整case校准含评价的ETA，当前耗时为规划估计。

研究主线仍RGB–DSM双向条件互补与退化/缺失分割；恢复旁支。旧geometry gate不重开，oracle不等于可部署收益或mIoU上界，两个匹配专家与旧五专家的差不能唯一归因于训练混杂。门禁失败只停止/待解释，不自动重试旧配方、追加训练seed、learned DSM adapter或冻结DINO额外臂；不访问Test6/held4/final。20mask不是多训练seed/独立地点，也不预先声称方法学新颖性。

最后服务器查询仍2026-10-13T11:35:58.181880+08:00；原Phase1.5队列完成观测11:31:16.761032，GPU100/D160/E120完成且controller=False；上传9d7c27e8已接收，全载荷审计与科学分析在b3546315完成。本次无新实时服务器查询。

下一步按完整设计实现公共训练入口和资源调度，当前不能运行旧Phase1.5 enqueue/accelerate来启动Phase2。重要科学原件与历史失败均保留。