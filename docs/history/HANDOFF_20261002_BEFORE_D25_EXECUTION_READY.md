# 当前交接：D24复核完成、Pair无效消融纠正，D25八组待实现

更新2026-10-02（Asia/Shanghai）。权威分支rebuild-v1-protocol-20260915；[上次交接归档](../history/HANDOFF_20261002_BEFORE_D24_FULL_REVIEW.md)。

最后服务器队列观测2026-10-02T04:06:59.332637+08:00 COMPLETE 15/15。完整轻量原件已上传acd2dbfbcf18ef792840bfe3f5465207a74a13c2，共564文件；不再要求上传同一批。[复核报告](../experiments/D24_REVIEW_AND_PAIR_CORRECTION_20261002.md)中64个载荷SHA、3360逐tile/1680pooled矩阵及15组完成绑定已核对。权重/预测仍在服务器，未重新训练或推理。

重要纠错：绑定源码按大写Pair检查小写anchored_pair配置，A1/A3实际未施加Pair损失。必须撤回“Pair无增益/失败”，原screen false仅历史程序输出；Pair科学状态为无效消融/未决。源码已修枚举并记录enabled_steps、weighted_loss_sum，真实配置回归测试旧代码失败、修正后两项PASS。本地检查不等于服务器补跑；下一计划只在last4补一个匹配修正比较。

其他13组仍可比较：last4带来综合+2.986759；D1 Q-only综合86.444780/clean87.070670但DSM全缺失82.474159；A2 QD综合86.293907/clean86.903466、全缺失86.143073。缺失能力和完整精度有取舍。当前类原型/类别平衡、固定旧教师区域KD不支持确认；不能泛化为整个语义或KD思想失败。主问题仍是光学可用时DSM有益融合、退化与缺失，C1恢复旁支、部分解冻强基线；未改论文方向或最终贡献。

[近期文献映射](../literature/D25_OPTIMIZATION_AND_MISSINGNESS_20261002.md)连接DGL、ConD、RTFDNet、SGMA、SimMLM、传感器故障基准与PCGrad。SGMA官方仓库本次仍README/coming soon，ConD/RTFDNet是预印本；不要把本地改写写成完整复现。

[D25建议计划](../protocols/D25_MISSINGNESS_OPTIMIZATION_PLAN_20261002.md)：8组×4000，两个新假设为分开decoder和完整/缺失梯度冲突；有参数数量、同模长方向否证、同M0初始化光学对照，另含Pair纠错。均同D21 M0初始化，不能从已挑选D1续训而省略预算。32k更新、seed42开发筛选；最多两条通过后另立确认。新入口/模型尚未实现，用户本轮只要求规划，无新训练启动，也不要恢复已完成D24。

下一工作：按已写协议实现D25、冻结具体配置，验证真实增量目标/梯度路径和局部回退，之后再提供固定版本服务器命令。沿用GPU0/1两H10080GB、充足RAM/磁盘、物理batch16、nohup，全部文件在/home/jovyan/zzx下D25新目录；不重做资源/预算审计。服务器由用户终端执行，无SSH直连。

Test6禁读；Val2反复开发、held4历史Train16暴露，均不能冒充独立final。梯度冲突尚未被本实验测量，D25是检验而非已有结论。频率暂不添加，未来是否保留取决于稳定强基线下独立增量，不是永久否定频率路线。
