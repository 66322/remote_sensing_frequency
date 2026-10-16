# 当前状态：工程原件待上传与核验

更新2026-10-01；分支rebuild-v1-protocol-20260915，实验基准1a8a840，D23工程执行入口40fca5adf4ded1277de264ffc361b67fbaaca0c8。用户服务器终端执行，助手无服务器直连。

用户决定：两台电脑轮流工作，GitHub为共享记录权威入口；长输出直接上传GitHub，助手回读，用户仅回传提交号。所有服务器文件在/home/jovyan/zzx对应实验目录。两卡GPU0/1 H10080GB可用，内存/磁盘充足。见[共享规则](../protocols/RECORD_SOURCE_AND_HANDOFF.md)和[上传规则](../protocols/LIGHT_RECORD_UPLOAD_20261001.md)。

研究阶段仍为可行性探索：频率＋语义可靠性与模态缺失/退化训练推理为优先候选；C1旁支，部分解冻强基线。允许换解法/问题/方向，章节贡献未冻结。[研究决策](RESEARCH_DECISION.md)。D23-A标签互补均值+1.888456pp只支持准备B；门控精度、频率独立增量和泛化尚未成立。

工程已实现专家固定8前向、gate batch16两视图合并loss单次backward，无gate梯度累积，8组/6固定/14条件和原机制/风险门槛不变。22项本地CPU检查通过。

最新用户片段：GPU1最后观测2026-10-01T14:07:44.235024+08:00，profile ENGINE_ADMISSION_COMPLETE；TSF12步与重载相等，步中位0.18741658秒，整图3条件共98.162秒。CPU紧凑报告22项PASS。GPU0片段仍缺完整完成头部与身份，不能称双卡原件完整验收。服务器归档SHA e290548c50758e3d228f6e00e4e36bf4592efcf5daf2739994b6a28ee18278fa、29924字节；未上传原件。[证据边界](../experiments/D23_B_ENGINE_RECORD_UPLOAD_PREPARATION_20261001.md)。

立即动作：用户执行轻量上传工具，从已有目录上传summary/preflight/日志/compact及索引到同一GitHub分支；助手读原件核验。工具本地模拟检查通过，真实上传未执行。随后解决12tile缓存/TCAP I/O和双卡并行预算，冻结runtime lock才生成8组4000步队列。最后记录formal_training_started=false，正式锁/队列尚未生成。[下一步](NEXT_EXPERIMENT.md)。

频率无独立增量则撤回对应贡献；gate无收益关闭具体解法，不自动降阈值或补seed，C1不自动升级主线。光学整幅缺失、未知缺失识别、独立泛化及历史原件归档仍未解决；Test6历史暴露且禁读。此前完整交接保留docs/history/20261001_before_light_record_upload/，历史负结果不重复开启。
