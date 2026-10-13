# 下一步：Phase1.5完成上传核验，再制定配对训练

## 上传状态补充：本地归档已提交，GitHub推送认证失败（2026-10-13用户回报）

用户粘贴上传尾部显示大量create mode，随后 `Invalid username or token` / `Password authentication is not supported for Git operations` / fatal Authentication failed；upload_phase15.py在git push（exit128）处退出。失败工作树 `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase15_recoverability_20261012T233532_842792/github_upload_20261013T113931418057_1206639`，证据路径 `records/research_phase15_recoverability_20261012T233532_842792/evidence_20261013T113931418057_1206639`。这是上传认证故障，实验完整完成态不变，记录仍在服务器；没有PHASE15_GITHUB_COMMIT或成功push回报。仅凭错误无法确定输错/令牌失效/权限不足，凭据不接收或记录。

下一步复用该worktree：fetch权威分支→将仅轻量记录的未推送本地提交rebase到FETCH_HEAD→正常push（不force）。不重跑upload_phase15.py，不重新生成或重复登记证据。读取最终rev-parse HEAD并回传，之后接收原件与独立分析。重要记录已同步远端导致head推进，恢复前fetch/rebase是保留共享入口更新所需。

现有上传脚本按白名单递归保存全部JSON/JSONL/log/py/md/txt，JSON精确压缩编码，数组仅SHA/路径索引、不上传权重/预测本体。1540逻辑case的CM/逐类/绑定、100批凭据、280 CPU分析与smoke/故障/接管及源码导致文件多；继承完整旧源码/测试和部分进度/日志有冗余，不能把文件数当大小。每次重复运行会另建完整evidence快照，终端git commit还打印每个create mode。后续可设计精简manifest+JSONL打包/精确归档、源码引用+改动/故障日志优先、上传幂等/只retry现有提交及简洁输出，保留逐case原计数/SHA/去留证据；本次尚未修改冻结上传脚本或删除已归档文件。

[用户上传失败摘录](../../records/research_phase15_recoverability_20261012T233532_842792/upload_authentication_failure_20261013.json)。


## 最后观测与下一步

最后用户只读查询 **2026-10-13T11:35:58.181880+08:00**；queue LAST_OBSERVED **2026-10-13T11:31:16.761032+08:00**，**PHASE15_COMPLETE_AWAITING_REVIEW / CONTROLLER_LIVE=False / GPU100 COMPLETE**。新controller.log回报 `PHASE15_COMPLETE NO_AUTOMATIC_TRAINING`。D progress **11:31:06.225282**：**160/160**，tile5_10/realization20/matched、parallel_workers2、preserved63/new97、elapsed1595.456915秒（26分35.5秒），合计吞吐16.448秒/完成case。保留63旧结果、计算97剩余已确认；两真实case等价PASS仍为11:04:30回执，非全160科学验收。

本轮技术执行/五项汇总已返回完成，GPU和CPU任务结束；不能凭完成态宣布研究假设成立。当前 **COMPLETE_AWAITING_LIGHT_EVIDENCE_UPLOAD_AND_INDEPENDENT_REVIEW**，完整summary/CM/逐类计数/绑定轻量原件尚未接收。之前11:30–11:45的D条件ETA不再是剩余时间，剩余计算为0，科学核验仍待上传。以上是最后观测，不是实时查询。


原目录 `/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase15_recoverability_20261012T233532_842792`；推理commit45138f0f92c668bc86ce9532a4382b38d2b12b6d；加速子目录 `cpu_acceleration_20261013T110244_1189050`，加速commit4842b5eb38c62b19db97094d88526260f5fe3359。原失败目录research_phase15_recoverability_20261012T232212_836118与受控停止证据均保留。不再次enqueue/accelerate。

立即下一步：用户终端前台运行原目录 `PY -B DIR/code/scripts/upload_phase15.py --directory DIR --root /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro`。入口重新验证完成summary/job绑定、所有owned进程退出及锁释放后上传，不执行计算。保留code/CPU接管前后状态/受控停止回执/两真实等价/原SHA及新caseacceleration来源；数组/权重留服务器。返回PHASE15_GITHUB_COMMIT后回读清单/载荷、复算A/B/C/D/E原计数与去留条件，分析模块和训练轨迹，再制定真正配对训练；不自动新训练或追加seed，不访问Test6/held4/final。


[用户完成回报](../../records/research_phase15_recoverability_20261012T233532_842792/cpu_acceleration_20261013T110244_1189050/user_reported_completion_20261013T113558.json)。

## 资源使用决定

2026-10-13用户要求充分使用内存、并行分析和实验数据预加载，并回传free -h：total1.9Ti/available1.8Ti/used11Gi/free1.8Ti/shared2.3Gi/buff-cache19Gi/swap0。仅用户主机free输出，无独立时间戳/容器quota/affinity回报，不直接当进程可用内存或CPU核数。已将大内存驻留与并行作为后续默认工程策略：CPU case并行初选8（受实际CPU quota/affinity及内存限制并经小规模吞吐校准），工作集按清单一次SHA校验/解压、只读驻留并复用，必要时共享只读cache避免重复副本。缓存预算≤实际可用内存50%，预留数值临时数组和其他任务资源，不为“吃满”强制分配。数值库每进程线程数与case进程数分开控制，不直接把OMP改成最大值。

源码核对：Post-T训练已经fit12全tile驻留、PrefetchedBatches(16,8,4,True)，8线程共享内存crop预取、4batch预取及pin_memory/non_blocking传输；不是每步重读磁盘。后续优化先测data-wait/计算时间，再调预取；保持batch/采样序列/seed/精度/训练预算/验证口径及batch_hash不变。

已新增ResidentArrayCache与recommended_profile工程组件，2项CPU检查通过（16次8线程请求仅装载1次、15命中、数组一致且只读、SHA/修改拒绝、预算/资源限制），尚未接入当前immutable运行或服务器实测；不能写成当前全部预测已驻留。采纳资源策略时剩47case、约13分钟，因此继续原2进程收尾；现已完整完成，未做第二次接管或全量预加载。新缓存/并发策略用于后续独立执行包，不改变科学主线或新增训练任务。

## 科学角色和边界

主线仍RGB–DSM双向条件互补与退化/缺失分割；任务驱动恢复旁支。唯一当前研究问题可恢复性分解E/A/B/C/D，routing与residual context均为条件候选。当前0训练、100固定GPU工作批/1540逻辑case、160D统计case，无自动新seed/Test6/held4/final；用户允许GPU0/1、至少一天且未完继续，无24h截止。不为填时长追加任务。

旧Post-T最后上传观测2026-10-12 11:03:22.917566+08:00：8/8COMPLETE/PAIRED_SCREEN=False；Structured 16:32:44.762198：42/42COMPLETE/NO_SUPPORT_THIS_PROTOCOL。R16−H16+0.348562pp局部通过，整体失败来自5/6 E−R0底线；S1主PE+0.122522pp CI跨0，不重开旧gate、不盲目续训。科学问题、路线角色、去留条件以RESEARCH_DECISION与原协议/证据为准。

先读[研究决定](RESEARCH_DECISION.md)、[新交接](NEW_CHAT_HANDOFF_20261011.md)、[CPU接管协议](../protocols/PHASE_1_5_CPU_ACCELERATION_20261013.md)、[资源策略](../protocols/LARGE_MEMORY_PARALLEL_POLICY_20261013.md)、[主诊断设计](../protocols/PHASE_1_5_RECOVERABILITY_20261012.md)、[实验索引](../experiments/rebuild_v1/INDEX.md)。。上一版含历史进度的入口已归档[NEXT_EXPERIMENT.md历史版](../history/pre_resource_policy_20261013/NEXT_EXPERIMENT.md)。
