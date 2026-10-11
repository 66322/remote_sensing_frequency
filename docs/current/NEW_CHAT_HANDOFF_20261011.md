# 当前交接：8k训练步数已满，R8终点评价与16k阶段等待

权威共享源：66322/remote_sensing_frequency / rebuild-v1-protocol-20260915。本次接收23:34进度并核对GPU排期；没有新启动/重启任务。

## 最后观测与当前执行

最后服务器只读查询2026-10-11T23:34:24.796568+08:00：queue观测23:34:17.832878、RUNNING、controller LIVE=True。CONTENT_PRE/H8/F8 COMPLETE且worker退出；H8/F8均8000步。R8 GPU1 RUNNING/LIVE=True、8000/8000、phase=endpoint_ordinary（3_11/aux_down4，529/529窗口仅指该case）。R16/H16/F16/CONTENT_POST PENDING。3/8整项完成、1项评价中、4项待办；训练更新回报24000/72000，R8尚未完成整项技术验收。此为最后观测，不代表实时状态。

H8/F8完整worker耗时10338.760/10277.432秒（约2h52m/2h51m）；R8当前6936.955秒且仍评价。remaining_train_hours=0仅表示训练步数已满，不表示任务已结束。没有本轮精度或DSM内容原件，loss差不能作方法结论。

GPU0空闲可由原8k→16k阶段依赖解释；status回报未包含gpu_blocked字段，不能仅据利用率断言release状态。控制器需H8/F8/R8整项COMPLETE并完成三组batch配对检查后才派发16k。若两卡启用、无外部占卡且技术检查通过，按现代码GPU0→R16、GPU1→H16，先完成卡→F16。无需重复enqueue、rejoin或手动启动worker。

原目录research_post_t_paired_v2_20261011T182543_3880702、执行44e4df5afbaeb603e6441e7ef14ff09f228bc027、controller登记PID3881013不变。六训练F/H/R×8k/16k共72000更新，前后各24内容诊断case；固定R16主候选，8k后三组不按分数淘汰。继续原队列，不重复登记或启动。用户需要某卡时保存退出并移交剩余卡续跑，被释放卡显式rejoin前停用；无24h全队截止，失败HOLD不自动重试。

[原查询](../../records/research_post_t_paired_v2_20261011T182543_3880702/user_reported_progress_20261011T233424.json)、[执行/查询/释放操作](../protocols/POST_T_PAIRED_V2_EXECUTION_20261011.md)、[科学配对细则](../protocols/POST_T_PAIRED_ADAPTATION_BUDGET_20261011.md)、[本次之前交接原文](../history/PRE_STRUCTURED_FAILURE_DESIGN_HANDOFF_20261011.md)。

## 研究角色、依据与本次建议

阶段仍为可行性探索和机制定位。主线RGB–DSM双向条件互补与退化/缺失分割；任务驱动恢复为旁支。既有证据限Potsdam fit12→重复Val2 3_11/5_10、seed42、已知RGB局部缺失。旧T7/U/E=False保持，不后验改选M303/T5；不声称双向、未知故障或独立泛化。

用户要求结合所附“下一阶段实验执行规划”作综合分析。[评审草案](../protocols/STRUCTURED_FAILURE_EVAL_V0_20261011.md)、[原附件](../../records/structured_failure_design_review_20261011/user_proposal.md)、[拟议矩阵](../../records/structured_failure_design_review_20261011/planned_design.json)已归档。状态DESIGN_REVIEW_DRAFT_NOT_REGISTERED；仅文件设计，生成器、真实mask、known-answer测试、GPU队列均未实施。新增训练0、推理0；不是主线变更决定。

建议Phase 0完整验收→Phase 1A四固定系统×四掩码族×20实现×两tile（640缺失case＋8clean，0训练）→按结果选择一类真正配对训练。主PE模型预设S1-0；同权重M000_masked/context测上下文策略；U-block-random与U-block-matched分别服务形态与落点问题。20是掩码实现数，不是训练seed或独立地区。匹配算法、采样规则与部分参数仅为设计值，须先做不读取模型结果的CPU可行性核验再冻结。

未采纳附件中的S1-3−S1-0直接归因上下文、边缘结果自动20→40、一次展开全部block尺寸/GT boundary、默认router/oracle梯度升级、立即新残差训练。随机像素可能比块更伤害特征支持；healthy膨胀后可能为空；R0是可实现参考而非GT oracle；硬掩码支持外exact下输出蒸馏不能证明学到保护。

下一不确定性：同预算R是否优于H/F且过R0/保护底线；DSM内容是否真正被利用；类别与primitive几何受控后是否仍有结构落点损伤及上下文交互。草案保留STRUCTURED_SIGNAL / INCONCLUSIVE / NO_SUPPORT_THIS_PROTOCOL三种结论，不确定不自动扩样。结构线索失败不否定一般上下文适应，当前RGB子问题成功也不等于双向贡献。

## 立即下一步

按[具体排期](../protocols/POST_T_PAIRED_RESOURCE_SCHEDULE_20261011.md)继续原队列：R8完成与三组配对检查通过后，预计双卡自动接R16/H16，再接F16；完成后显式上传轻量原件，独立复算完整配对、轨迹、内容和保护。CPU开发可先行规划，新GPU诊断需生成器/计数/同源端点验收、原队列结束与资源查询后安排。用户释放的卡供用户使用，不自动接Phase 1。具体新训练组数和预算待证据后冻结，不填入执行registry。

服务器终端由用户执行、无SSH；全部运行记录与代码快照保存在/home/jovyan/zzx对应目录。Test6/held4/final保持关闭；不自动失败配方重跑、增加训练seed或开恢复旁支。
