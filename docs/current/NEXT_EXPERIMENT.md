# 下一步：注册GPU0自动后继，完成原阶段原件验收

2026-10-09用户授权规划并自动接续；2026-10-10完成实现与发布。新增冻结S1-0主干的私有解码器移植，五种初始化（S1-0/1/2/3及随机）×屏蔽/保留上下文，共T0—T9十组，各新8000步、seed42，固定T7。只用GPU0、单worker；不重训原P、不触发Q。执行协议见[GPU0后继协议](../protocols/POST_S1_TRANSFER_GPU0_20261009.md)。

后继代码已实现并完成CPU检查，**尚未收到服务器注册回报**。用户执行一次enqueue_post_s1_transfer.py后，nohup控制器自动等待前序SUPPORT_COMPLETE_AWAITING_REVIEW、CPU/D1/十P/E全部COMPLETE、原产物及SHA验收、原controller/worker退出和锁释放，再取得共享租约及GPU0空闲才接续。技术异常HOLD，不重启原队列；前序P7科学gate=False不阻断这个新研究问题。

1. 用户执行一次发布的bootstrap注册指令；保存TRANSFER_QUEUE_REGISTERED目录/PID/log回报。等待期显示WAITING_PREDECESSOR。
2. 原阶段全部结束并释放后，新控制器自动验收并运行T0—T9，不需要手动逐组启动。原失败或未释放时HOLD/WAIT，不自动修复。
3. 原Post-S1全批上传并分析P3/P0/P1/E，保持P7原失败。新阶段运行与旧结果上传可独立进行；协议不根据后收到的E改候选。
4. 首格实际训练/评价耗时校正剩余时间；新阶段完成后上传新轻量记录，验证混淆矩阵/联合边际/绑定，再按固定T7门槛和全因子描述验收。

已验收七P结果：P7 RGB_U 83.575357%，比匹配P6 +1.759726pp，两tile正；但低于零训练R0 1.426292pp，原固定门槛失败。D1 DSM必要信号失败，Q不运行。P3/P0/P1/E尚未收全，不后验换候选或改旧结论。[阶段分析](../experiments/POST_S1_PARTIAL_RESULTS_20261009.md)。

最后已接收快照捕获2026-10-09T21:43:00.478470+08:00，queue最后观测21:42:23.635611、RUNNING_P3、PID1890742；P6/P7/P8/P9/P4/P5/P2完成，P3运行，P0/P1/E待执行。这是历史观测，不是本次实时服务器查询。

主线仍RGB–DSM条件互补与退化/缺失分割，可行性探索；任务驱动恢复旁支。冻结旁路与解码移植不是创新承诺。本轮仅检验局部RGB缺失，Potsdam fit12/Val2 3_11、5_10，native512/stride256、NoBoundary fg5主，Full/六类诊断；Val2和E是重复开发证据。禁止GPU1、Test6、held4、独立final、预留T规则、增加seed或失败自动复跑。
