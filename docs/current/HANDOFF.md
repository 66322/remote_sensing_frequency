# 当前交接：GitHub为共享记录，D23工程尾部已核对

更新2026-10-01；分支rebuild-v1-protocol-20260915，执行入口40fca5adf4ded1277de264ffc361b67fbaaca0c8，实验基准1a8a840。用户终端执行，本地无服务器直连。

用户决定：两台电脑轮流工作，记录以GitHub为准，可写回GitHub。本地仅工作副本；开始任务先读远端[START_HERE](../START_HERE.md)与[共享记录规则](../protocols/RECORD_SOURCE_AND_HANDOFF.md)，不使用旧main缓存推断状态。

研究仍为可行性探索：频率＋语义可靠性及缺失/退化训练推理优先候选，C1旁支，部分解冻强基线；允许换解法/问题/方向，章节和贡献未冻结。[研究决策](RESEARCH_DECISION.md)。

D23-A最后有明确结束时钟观测2026-10-01T12:44:35.075903+08:00 COMPLETE，标签选择互补诊断均值+1.888456pp，仅通过B准备门槛。A原件归档报告SHA041bc0ad79c3c5f11fdbf4a29479b2c3cf68d60f898b5125d8cf2211e59084b1，尚未接收原件。

17be568两卡数值诊断回传无结束时钟，训练tile2_12裁剪上micro2/4/8输出一致、micro16少量可重复差异。用户明确H10080GB后，本轮实现专家固定8前向＋gate batch16两视图合并loss单次backward；取消gate累积，不改变有效batch/研究门槛。[入口说明](../protocols/D23_B_ENGINE_ADMISSION_20261001.md)。22项本地CPU检查通过。

最新用户粘贴仅工程summary尾部，目录records/research_d23_b_engine_admission_20261001T140528_658274：两项整图缺失条件的6条原矩阵/fg5复算一致，missing harm/rescue为0、logits相等为服务器报告；尾部98.162秒、显存allocated2.272GiB/reserved2.820GiB、RSS9.403GiB。附件缺设备身份、完成时钟、训练耗时/签名及CPU/GPU0完整头部，不能写成两卡完整验收PASS。详见[尾部核对](../experiments/D23_B_ENGINE_TAIL_AUDIT_20261001.md)与[解析原计数](../../records/research_d23_b_compact_20261001/user_pasted_engine_tail.json)。formal_training_started=false。

立即动作：读取已有两个summary/preflight和CPU日志，输出紧凑完整绑定及轻量索引，不重跑已做任务。完整验收后，继续12tile缓存/TCAP I/O与双卡预算，冻结runtime lock才生成8组4000步队列。正式锁/自动队列未生成，当前无正式训练。[下一步](NEXT_EXPERIMENT.md)。

8组、6固定比较、14条件、NoBoundary fg5及机制/风险门槛保持。频率无独立增量撤回相应贡献；gate无收益关闭具体解法，不自动改阈值/加seed，C1不自动升主线。光学整幅缺失、未知缺失识别、独立泛化及旧原件归档仍未解决；Test6历史暴露且禁读。

所有服务器记录在/home/jovyan/zzx对应实验目录，不覆盖或移动。原件在服务器不等于已上传GitHub，当前原计数JSON源为用户片段。旧交接归档docs/history/20261001_before_github_primary_engine_tail/。
