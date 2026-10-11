# 新对话交接：继续原双卡队列，下一阶段设计草案已归档

权威共享源：66322/remote_sensing_frequency / rebuild-v1-protocol-20260915。本次仅综合评审用户附件，不启动新评价或训练。

## 最后观测与当前执行

最后服务器查询2026-10-11T18:54:08.952037+08:00，queue观测18:54:02.365173，RUNNING/controller LIVE=True。CONTENT_PRE COMPLETE并退出，H8 GPU0、F8 GPU1各180/8000且LIVE=True；R8/R16/H16/F16/CONTENT_POST PENDING。此为最后观测，不代表实时状态。没有新精度或内容诊断原件。H/F训练步速约0.663/0.653秒；只覆盖训练计算，R与整队耗时未校准。

原目录research_post_t_paired_v2_20261011T182543_3880702、执行44e4df5afbaeb603e6441e7ef14ff09f228bc027、controller登记PID3881013不变。六训练F/H/R×8k/16k共72000更新，前后各24内容诊断case；固定R16主候选，8k后三组不按分数淘汰。继续原队列，不重复登记或启动。用户需要某卡时保存退出并移交剩余卡续跑，被释放卡显式rejoin前停用；无24h全队截止，失败HOLD不自动重试。

[原查询](../../records/research_post_t_paired_v2_20261011T182543_3880702/user_reported_progress_20261011T185408.json)、[执行/查询/释放操作](../protocols/POST_T_PAIRED_V2_EXECUTION_20261011.md)、[科学配对细则](../protocols/POST_T_PAIRED_ADAPTATION_BUDGET_20261011.md)、[本次之前交接原文](../history/PRE_STRUCTURED_FAILURE_DESIGN_HANDOFF_20261011.md)。

## 研究角色、依据与本次建议

阶段仍为可行性探索和机制定位。主线RGB–DSM双向条件互补与退化/缺失分割；任务驱动恢复为旁支。既有证据限Potsdam fit12→重复Val2 3_11/5_10、seed42、已知RGB局部缺失。旧T7/U/E=False保持，不后验改选M303/T5；不声称双向、未知故障或独立泛化。

用户要求结合所附“下一阶段实验执行规划”作综合分析。[评审草案](../protocols/STRUCTURED_FAILURE_EVAL_V0_20261011.md)、[原附件](../../records/structured_failure_design_review_20261011/user_proposal.md)、[拟议矩阵](../../records/structured_failure_design_review_20261011/planned_design.json)已归档。状态DESIGN_REVIEW_DRAFT_NOT_REGISTERED；仅文件设计，生成器、真实mask、known-answer测试、GPU队列均未实施。新增训练0、推理0；不是主线变更决定。

建议Phase 0完整验收→Phase 1A四固定系统×四掩码族×20实现×两tile（640缺失case＋8clean，0训练）→按结果选择一类真正配对训练。主PE模型预设S1-0；同权重M000_masked/context测上下文策略；U-block-random与U-block-matched分别服务形态与落点问题。20是掩码实现数，不是训练seed或独立地区。匹配算法、采样规则与部分参数仅为设计值，须先做不读取模型结果的CPU可行性核验再冻结。

未采纳附件中的S1-3−S1-0直接归因上下文、边缘结果自动20→40、一次展开全部block尺寸/GT boundary、默认router/oracle梯度升级、立即新残差训练。随机像素可能比块更伤害特征支持；healthy膨胀后可能为空；R0是可实现参考而非GT oracle；硬掩码支持外exact下输出蒸馏不能证明学到保护。

下一不确定性：同预算R是否优于H/F且过R0/保护底线；DSM内容是否真正被利用；类别与primitive几何受控后是否仍有结构落点损伤及上下文交互。草案保留STRUCTURED_SIGNAL / INCONCLUSIVE / NO_SUPPORT_THIS_PROTOCOL三种结论，不确定不自动扩样。结构线索失败不否定一般上下文适应，当前RGB子问题成功也不等于双向贡献。

## 立即下一步

继续原双卡任务，由用户按需查询；完成后显式上传轻量原件，独立复算完整配对、轨迹、内容和保护。CPU开发可先行规划，新GPU诊断需生成器/计数/同源端点验收、原队列结束与资源查询后安排。用户释放的卡供用户使用，不自动接Phase 1。具体新训练组数和预算待证据后冻结，不填入执行registry。

服务器终端由用户执行、无SSH；全部运行记录与代码快照保存在/home/jovyan/zzx对应目录。Test6/held4/final保持关闭；不自动失败配方重跑、增加训练seed或开恢复旁支。
