# 当前交接：D30四项解读与后接18＋4实现

主问题仍为RGB外观/语义与DSM高度/几何的双向条件互补及任一模态退化/缺失下的可靠分割。处于论文可行性探索，频率、语义可靠性、专家与共享/私有只是候选解法；任务驱动SR/恢复仍为旁支，没有自动转向或确认性贡献。

最后用户回传为2026-10-04 00:08启动日志（时间取目录名，日志行无独立时间戳）：Post-D30控制器PID2450552已由nohup启动，CPU检查通过，记录`PORTFOLIO_WAITING_D30 RUNNING`，即已排队等待D30。执行commit固定01ec8dee82f7e272f6a650aaf9f3e619a0e7c516，新目录`research_post_d30_mechanisms_20261004T000812_2446364`；所给日志尚无新GPU worker启动。没有/proc直接存活检查或完整queue_status回传，不能把此次日志当作持续实时存活保证。D30在该日志中被间接观测为RUNNING；其最后直接进度仍为10月3日23:17，随后四项完成指标已分析，PR_area/PR_pixel、重放效果及原矩阵待收。

用户授权：根据D30结果执行已规划机制并增加有解释价值的组数。实现A→B→C→条件F，等D30六项全部完成、有效screen、锁释放且无其活跃worker后接力；新目录独立、全局后继锁防重复。D30失败HOLD，新阶段技术失败停止后继，不自动杀进程或重复训练。断线用nohup；显式resume恢复保存状态，完成结果保留。

四项效果：P−S0综合+0.041182/+0.066432pp，R−S0−2.013409/−2.053585pp（selected/fixed8000）。R多保留DSM独有正确但损害RGB原正确；保护仍丢DSM有用信息。2×2交互+0.176568/+0.162126pp，不能称负交互根因。指标来自用户终端回传，尚未从原矩阵独立重算。

[四项结果分析](../experiments/D30_FOUR_ARM_REVIEW_20261003.md)、[执行协议](../protocols/POST_D30_EXECUTION_20261003.md)、[机读计划](../../records/research_post_d30_design_20261003/plan.json)。

新增6诊断组：A4/A5=.03/.3、B5/B6=3×3/7×7、C4/C5=单向KD。主体共18组144000更新；F4再32000，仅固定B3全部通过才运行。原D27/D28/D30阈值和D29关闭状态不变，未自动多seed。代码实现＋10项CPU合成测试通过；原生checkpoint/CUDA真实运行待服务器首个正常组。

实现澄清：所有新组去掉质量候选aux_shift8，统一halo-safe裁剪，隔离小错位增强；A0是新匹配基线。C两个缺失学生只看自身模态，全模态沿冻结B0；F去HF在旁路前，避免绕过。几何8px评分支持不送入模型。主protocol机读配置/代码一致。

root=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro；D30=records/research_d30_loss_decomposition_20261003T205144_2349167，执行9db12dfb7ee85dff91dd6c246c7f161b60aca603；新目录records/research_post_d30_mechanisms_20261004T000812_2446364，控制器PID2450552，执行01ec8dee82f7e272f6a650aaf9f3e619a0e7c516。固定teacher为D26 B0 selected4000，原RGB/DSM checkpoint与SHA继承D30计划。

下一步：按[NEXT](NEXT_EXPERIMENT.md)只读查询已有队列，核对存活和D30释放后的接力；不要重复创建队列；收齐D30最后两项与原件；不重审资源。全部新结果可用upload_post_d30_records.py写回同分支。

只使用物理GPU0/1，两张H10080GB；RAM/磁盘充足，无资源探针。seed42、8000步、batch16无累积、nohup。快照、临时、缓存、日志全部在/home/jovyan/zzx对应实验目录。用户在服务器终端执行，无SSH；Test6与独立final禁读。重复开发Val2不是确认性泛化证据。GitHub本分支为共享权威，大预测/checkpoint本体留服务器并索引。

[历史交接](../history/pre_post_D30_execution_20261003/HANDOFF.md)。

[本次启动观测](../../records/research_post_d30_mechanisms_20261004T000812_2446364/launch_observation_20261004T000812.json)。
