# 当前交接：补A评价后恢复B/C队列

最新用户回传：2026-10-04 08:12:18（由服务器日志文件时间标识）已通过nohup启动恢复，PID2698383，repair commit=9df2bf44a03955a0db43de1538aff1c91bfae33d。日志打印PORTFOLIO_REPAIR_CHECKS_PASS runtime_conditions=32；修复快照evaluation_repair_20261004T081218353451_2698383。此次回传未包含后续worker启动、PID存活查询或补评价完成证据，不能宣称A已恢复完成。不要重复执行启动指令，先只读查询已有恢复。

主问题保持RGB外观/语义与DSM高度/几何的双向条件互补，以及任一侧退化/缺失时的可靠分割。处于可行性探索，频率、可靠性、专家、共享/私有均是候选解法；任务驱动SR/恢复仍是旁支，未自动变更方向，也没有确认性贡献。

最后服务器观测：D30在2026-10-04T00:47:08.030508+08:00为COMPLETE，六项全部完成。Post-D30在2026-10-04T06:04:04.397991+08:00为COMPLETE_WITH_TECHNICAL_FAILURES；原控制器2450552已退出（Z、LIVE=False），无活跃worker。A0—A5均训练至8000步，均因评价条件`dsm_present_zero`未被处理而失败；0/18正式完成，B/C未启动，F仍待条件。不能据此评价A机制效果。原执行commit为01ec8dee82f7e272f6a650aaf9f3e619a0e7c516，原目录为`research_post_d30_mechanisms_20261004T000812_2446364`。该失败观测为06:04历史状态；08:12恢复启动检查已通过，后续执行状态待查询。

恢复在同一目录建立独立、带SHA清单的评价补丁快照，原plan和code快照保持不变。补丁按D27原语义支持present_zero及present_shift_half：DSM虽坏，但两侧可用性mask仍为True，不把未知坏数据当已知缺失。A必须加载8000步保存状态，新增优化器更新数为0，补评价前后核对selected/step8000权重SHA；相同checkpoint的已有评价可校验后复用。补齐A后仍按A→B→C→条件F；F仅由固定B3全部gate通过触发，不新增多seed、D29或新模块。

D30终端汇总：P综合86.092396，R84.037805，PR_area85.986496，PR_pixel84.759540，四项continue均False。相对S0综合86.051214，PR_area−0.064718pp、PR_pixel−1.291674pp；不同归一化未达到预设增量门槛。P的小改善与R的信息取舍仍成立，但不能据此认定唯一根因或整个双模态问题无效。指标为Potsdam开发Val2、native512/stride256、NoBoundary fg5的selected口径，来自用户终端；完整原矩阵尚待上传与独立重算。

已实现：评价兼容层、显式故障恢复控制器、权重/原快照绑定和补丁来源记录、修复来源上传、排除评价-only任务作为训练ETA样本。未来启动器检查实际继承计划的32个条件，而不是只检查D26基础计划。验证：5项修复测试、10项原机制CPU测试及Python3.10语法检查通过；不是服务器CUDA修复成功证明。服务器已执行恢复启动，32条件及修复回归检查通过；后续worker及完成情况按[NEXT](NEXT_EXPERIMENT.md)只读查询。

用户授权18主体＋4条件组、GPU0/1、已有队列后接。A对齐范围/强度、B局部对应与普通增强、C双向缺失蒸馏保持原对照和阈值；失败不扩大为研究问题无效，敏感性最佳组不替代固定主候选。已有6组训练保留，剩余12主体训练仍待启动。

[故障与恢复说明](../experiments/POST_D30_EVALUATION_REPAIR_20261004.md)、[原执行协议](../protocols/POST_D30_EXECUTION_20261003.md)、[机读设计](../../records/research_post_d30_design_20261003/plan.json)。

只使用物理GPU0/1，两张H10080GB，RAM与磁盘充足；seed42、8000步、物理batch16、无累积、nohup。快照/临时/缓存/日志均在/home/jovyan/zzx对应实验目录。用户在服务器终端执行，无SSH；不重复资源审计或预算探针。Test6及独立final禁止访问；重复开发Val2不等于独立泛化。GitHub本分支为共享权威，大预测/checkpoint保留服务器并索引。

[原始终端观测](../../records/research_post_d30_mechanisms_20261004T000812_2446364/failure_observation_20261004T060404.json)；[上一版交接](../history/pre_post_D30_evaluation_repair_20261004/HANDOFF.md)。
