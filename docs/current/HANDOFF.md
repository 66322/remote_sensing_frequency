# 当前交接：GPU0 T后机制诊断包就绪，待用户终端登记

2026-10-11用户补充：原T实验可能已全部完成，要求结合整轮结果再规划。GitHub回查仍为bce81d59f2fd188a5e500354c4c93be8b7771937，仅T0—T4原件；T5—T9及最终screen未上传，不能确认新完成状态。以下26项为已实现的候选后继，尚未登记；先接收完整T记录，再决定是否原样采用，不把部分证据规划当作全轮结论。

最后服务器证据仍为2026-10-10T21:28:41.841837+08:00，原T队列RUNNING_T5；T0—T4已收原件，T5运行、T6—T9待运行，固定T7未收。这是历史观测，不是实时查询。旧Post-S1最后观测2026-10-10T08:13:57.270242+08:00，已完整结束。

新后继POST_T_MECHANISM：READY_NOT_REGISTERED。26项固定推理（16模块包组合＋10个已有4000步checkpoint），296个模型×条件×tile单元，新增优化器更新0，仅GPU0。代码已实现、11项CPU检查通过；135个继承Python文件与原执行manifest核对一致，真实GPU/权重验收留服务器。尚无新目录/PID/执行回报。

用户授权：2026-10-10明确要求后继自动接力，并要求解释R0/训练程度/问题解决闭环。[协议](../protocols/POST_T_MECHANISM_GPU0_20261010.md)包含问题、证据、去留、边界；[研究决定](RESEARCH_DECISION.md)保持主线角色。

本次实现：enqueue/control/status/prepare/worker/summary/upload、模块包组合和11项CPU检查。继承固定T执行4bf69489f789e998b7bf3181d3b3057c6ff7c04e的135个Python文件，代码快照SHA已核；真权重/GPU未执行。最后结果分析仍见[旧P完整与五T报告](../experiments/POST_S1_FULL_TRANSFER_PARTIAL_RESULTS_20261010.md)。

旧上下文四配对+1.614～+2.844pp、新T1/T3匹配上下文约+1.436/+1.432pp，两tile正；上下文问题与部分解决已有开发证据。固定P7=83.575357%，T1/T3=83.856616/83.858189%，均低于R0=85.001650%；T3−T1仅+0.001573pp且tile异号，尚无额外迁移支持。上述仅Potsdam fit12→Val2 3_11/5_10、seed42、固定8000、native512/stride256、NoBoundary mIoU_fg5。

完整T验收并确认采用本候选包后：用户在服务器fetch本次发布提交，将scripts/enqueue_post_t_mechanism.py取到zzx下独立bootstrap目录并以原EXP_PY执行一次。先读原队列并去重；等待T0—T9全部完成、控制器/worker退出、前序锁释放后自动拿共享后继锁，GPU0空闲时串行26项。任何技术失败HOLD，不重跑或抢占。不访问GPU1/Test6/held4/final。估时接手后4—8h粗范围。

登记后只读新目录code/scripts/status_post_t_mechanism.py；完成后以upload_post_t_mechanism_records.py显式上传。原T新增完成原件仍通过原upload_post_s1_transfer_completed_records.py接收，固定T7原gate单独验收。自动后继可在原T科学gate失败时执行诊断，但不得将失败改判。

关键验收：M333_context逐像素复现R0、四因素固定配对、支持外保护、4000绑定及0/4000/8000轨迹、救回/伤害分母。冻结表征/私有解码器可能存在能力或兼容性瓶颈，仍是待验解释；未校准交换失败不证明信息缺失。结果之后才确定下一族训练，不提前兑现普遍有效承诺。

未采纳扩步/新seed/事后换候选/Q镜像训练。旧交接归档[本次规划前原文](../history/HANDOFF_BEFORE_T_MECHANISM_20261010.md)。

