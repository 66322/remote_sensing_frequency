# 研究决定：保留上下文线索，检验冻结特征上的解码能力复用

后继已由用户服务器终端注册：目录`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_s1_transfer_20261010T073327_2852696`，controller PID2852987，日志`nohup_20261010T073335566918.log`，执行提交4bf69489f789e998b7bf3181d3b3057c6ff7c04e。注册时前序最后观测2026-10-10T07:33:24.785318+08:00、RUNNING_E，接续判断WAITING_PREDECESSOR。注册成功尚不等于T0已启动；没有后续PID存活或新训练进度回报。

现在无需重复enqueue。原阶段E、最终汇总及技术验收完成，controller/worker退出并释放锁后，后继取得共享租约、确认GPU0空闲，自动运行T0—T9；异常HOLD。原科学P7 gate=False不改变此次新问题授权。仅GPU0、无失败自动重试、新seed、Q或其他家族。

当前无需再注册，先用新目录code/scripts/status_post_s1_transfer.py及nohup日志只读观察。原Post-S1全批仍需原上传脚本上传后分析E与剩余P记录；不因注册输出代替原件验收。

2026-10-09用户授权规划并自动接续；2026-10-10完成实现与发布。新增冻结S1-0主干的私有解码器移植，五种初始化（S1-0/1/2/3及随机）×屏蔽/保留上下文，共T0—T9十组，各新8000步、seed42，固定T7。只用GPU0、单worker；不重训原P、不触发Q。执行协议见[GPU0后继协议](../protocols/POST_S1_TRANSFER_GPU0_20261009.md)。

已验收七P结果：P7 RGB_U 83.575357%，比匹配P6 +1.759726pp，两tile正；但低于零训练R0 1.426292pp，原固定门槛失败。D1 DSM必要信号失败，Q不运行。P3/P0/P1/E尚未收全，不后验换候选或改旧结论。[阶段分析](../experiments/POST_S1_PARTIAL_RESULTS_20261009.md)。

主线仍RGB–DSM条件互补与退化/缺失分割，可行性探索；任务驱动恢复旁支。冻结旁路与解码移植不是创新承诺。本轮仅检验局部RGB缺失，Potsdam fit12/Val2 3_11、5_10，native512/stride256、NoBoundary fg5主，Full/六类诊断；Val2和E是重复开发证据。禁止GPU1、Test6、held4、独立final、预留T规则、增加seed或失败自动复跑。

决定来源是用户本次明确要求后继自动排队，非从任务顺序隐含换主线。新结构将原融合解码器复制为私有分支，供体只提供解码权重，基础双专家不变；十格同容量与预算、零步诊断和T7/T1/T6/T9控制分开判断容量、初始化与上下文。若T7不能接近R0或不能超过同容量控制，结束该移植假设，不自动延长预算挽救。旧P7/N3/N5/N2/C判断保持。

后继代码已实现并完成CPU检查，**已收到2026-10-10服务器注册成功回报**。本次已执行enqueue_post_s1_transfer.py；nohup控制器自动等待前序SUPPORT_COMPLETE_AWAITING_REVIEW、CPU/D1/十P/E全部COMPLETE、原产物及SHA验收、原controller/worker退出和锁释放，再取得共享租约及GPU0空闲才接续。技术异常HOLD，不重启原队列；前序P7科学gate=False不阻断这个新研究问题。

此前部分分析采用的快照捕获2026-10-09T21:43:00.478470+08:00，queue最后观测21:42:23.635611、RUNNING_P3、PID1890742；P6/P7/P8/P9/P4/P5/P2完成，P3运行，P0/P1/E待执行。这是历史观测，不是本次实时服务器查询。

未采纳：将P7保护构造当创新，忽略R0，未收齐E即宣称终验，后验换T候选，多种子/扩窗口救失败，DSM镜像Q，自动衍生其他家族。下一不确定性：跨主干解码权重是否兼容，以及收益来自初始化还是上下文支持。
