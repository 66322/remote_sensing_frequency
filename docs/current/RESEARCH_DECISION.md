# 研究决定：保留双向互补问题与既有机制对照

最新用户回传A0/A1 worker日志（未附新的服务器观测时间；日志会话始于2026-10-04T08:12:25，不能以此代替当前时刻）：两项RUNNING，均打印PORTFOLIO_REPAIR_EVAL_ONLY optimizer_updates=0 reused_rows=20；均已完成evaluation 3_11 dsm_present_zero及dsm_present_shift_half，并推进至evaluation 5_10 rgb_local_q1。原诊断条件阻塞已越过，补评价真实推进；尚未收到complete.json/COMPLETE观测，因此不宣称两项完整完成或最终权重不变校验已通过。上一带时间的队列观测为2026-10-04T08:14:26.221138+08:00，控制器2698383、A0/GPU0 worker2698740、A1/GPU1 worker2698743存活。其余A→B→C→条件F顺序保持，不重启。

主问题保持RGB外观/语义与DSM高度/几何的双向条件互补，以及任一侧退化/缺失时的可靠分割。处于可行性探索，频率、可靠性、专家、共享/私有均是候选解法；任务驱动SR/恢复仍是旁支，未自动变更方向，也没有确认性贡献。

决策来源：用户已授权18主体＋4条件组并在原队列后执行；这次因已诊断的评价接口错误恢复同一队列，不增加科学实验或更改选模/门槛。A2/B3/C2及条件F1仍为固定主候选；A强度、B范围、C单向KD只作诊断。D29关闭，无新增多seed或final开放。

D30终端汇总：P综合86.092396，R84.037805，PR_area85.986496，PR_pixel84.759540，四项continue均False。相对S0综合86.051214，PR_area−0.064718pp、PR_pixel−1.291674pp；不同归一化未达到预设增量门槛。P的小改善与R的信息取舍仍成立，但不能据此认定唯一根因或整个双模态问题无效。指标为Potsdam开发Val2、native512/stride256、NoBoundary fg5的selected口径，来自用户终端；完整原矩阵尚待上传与独立重算。

最后服务器观测：D30在2026-10-04T00:47:08.030508+08:00为COMPLETE，六项全部完成。Post-D30在2026-10-04T06:04:04.397991+08:00为COMPLETE_WITH_TECHNICAL_FAILURES；原控制器2450552已退出（Z、LIVE=False），无活跃worker。A0—A5均训练至8000步，均因评价条件`dsm_present_zero`未被处理而失败；0/18正式完成，B/C未启动，F仍待条件。不能据此评价A机制效果。原执行commit为01ec8dee82f7e272f6a650aaf9f3e619a0e7c516，原目录为`research_post_d30_mechanisms_20261004T000812_2446364`。该失败观测为06:04历史状态；08:14已确认控制器及A0/A1 worker存活；随后用户回传worker日志确认新评价越过故障点。

恢复在同一目录建立独立、带SHA清单的评价补丁快照，原plan和code快照保持不变。补丁按D27原语义支持present_zero及present_shift_half：DSM虽坏，但两侧可用性mask仍为True，不把未知坏数据当已知缺失。A必须加载8000步保存状态，新增优化器更新数为0，补评价前后核对selected/step8000权重SHA；相同checkpoint的已有评价可校验后复用。补齐A后仍按A→B→C→条件F；F仅由固定B3全部gate通过触发，不新增多seed、D29或新模块。

待解决问题：共享对齐是否超过普通融合及全对齐；局部对应是否超过仅增强；双向缺失KD是否超过直接任务头与同mask硬监督。只有真实补齐评价后才讨论A效果，不把技术失败列为方法失败。

能力分开报告：A/B/F已知可用性精确回退；C学习缺失能力；未知局部错误；独立地域泛化。两侧均无信息不承诺正常分割。标签及真实退化仅训练/离线评价，不进入推理。

[故障与恢复说明](../experiments/POST_D30_EVALUATION_REPAIR_20261004.md)、[原执行协议](../protocols/POST_D30_EXECUTION_20261003.md)、[机读设计](../../records/research_post_d30_design_20261003/plan.json)。

只使用物理GPU0/1，两张H10080GB，RAM与磁盘充足；seed42、8000步、物理batch16、无累积、nohup。快照/临时/缓存/日志均在/home/jovyan/zzx对应实验目录。用户在服务器终端执行，无SSH；不重复资源审计或预算探针。Test6及独立final禁止访问；重复开发Val2不等于独立泛化。GitHub本分支为共享权威，大预测/checkpoint保留服务器并索引。
