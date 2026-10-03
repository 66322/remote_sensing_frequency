# 当前交接：D30四项解读与后接18＋4实现

主问题仍为RGB外观/语义与DSM高度/几何的双向条件互补及任一模态退化/缺失下的可靠分割。处于论文可行性探索，频率、语义可靠性、专家与共享/私有只是候选解法；任务驱动SR/恢复仍为旁支，没有自动转向或确认性贡献。

D30最新直接运行观测仍为2026-10-03T23:17:45.146029+08:00，控制器2349619存活，PR_area2860/8000、PR_pixel2420/8000；这不是实时状态。随后用户回传S0/S1/P/R的selected及fixed8000完成指标，未包含PR_area/PR_pixel、重放效果或原矩阵。新18＋4队列已实现并通过10项CPU检查，**尚无服务器启动、排队或存活观测**；必须执行下一步里的nohup指令后才可称排队。

用户授权：根据D30结果执行已规划机制并增加有解释价值的组数。实现A→B→C→条件F，等D30六项全部完成、有效screen、锁释放且无其活跃worker后接力；新目录独立、全局后继锁防重复。D30失败HOLD，新阶段技术失败停止后继，不自动杀进程或重复训练。断线用nohup；显式resume恢复保存状态，完成结果保留。

四项效果：P−S0综合+0.041182/+0.066432pp，R−S0−2.013409/−2.053585pp（selected/fixed8000）。R多保留DSM独有正确但损害RGB原正确；保护仍丢DSM有用信息。2×2交互+0.176568/+0.162126pp，不能称负交互根因。指标来自用户终端回传，尚未从原矩阵独立重算。

[四项结果分析](../experiments/D30_FOUR_ARM_REVIEW_20261003.md)、[执行协议](../protocols/POST_D30_EXECUTION_20261003.md)、[机读计划](../../records/research_post_d30_design_20261003/plan.json)。

新增6诊断组：A4/A5=.03/.3、B5/B6=3×3/7×7、C4/C5=单向KD。主体共18组144000更新；F4再32000，仅固定B3全部通过才运行。原D27/D28/D30阈值和D29关闭状态不变，未自动多seed。代码实现＋10项CPU合成测试通过；原生checkpoint/CUDA真实运行待服务器首个正常组。

实现澄清：所有新组去掉质量候选aux_shift8，统一halo-safe裁剪，隔离小错位增强；A0是新匹配基线。C两个缺失学生只看自身模态，全模态沿冻结B0；F去HF在旁路前，避免绕过。几何8px评分支持不送入模型。主protocol机读配置/代码一致。

root=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro；D30=records/research_d30_loss_decomposition_20261003T205144_2349167，执行9db12dfb7ee85dff91dd6c246c7f161b60aca603；新目录research_post_d30_mechanisms_<timestamp>_<pid>。固定teacher为D26 B0 selected4000，原RGB/DSM checkpoint与SHA继承D30计划。

下一步：执行[NEXT](NEXT_EXPERIMENT.md)一次后接启动，回传POST_DIRECTORY和状态；收齐D30最后两项与原件；不重审资源。全部新结果可用upload_post_d30_records.py写回同分支。

只使用物理GPU0/1，两张H10080GB；RAM/磁盘充足，无资源探针。seed42、8000步、batch16无累积、nohup。快照、临时、缓存、日志全部在/home/jovyan/zzx对应实验目录。用户在服务器终端执行，无SSH；Test6与独立final禁读。重复开发Val2不是确认性泛化证据。GitHub本分支为共享权威，大预测/checkpoint本体留服务器并索引。

[历史交接](../history/pre_post_D30_execution_20261003/HANDOFF.md)。
