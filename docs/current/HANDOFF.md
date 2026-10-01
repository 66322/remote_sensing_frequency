# D23当前状态与交接（2026-10-01）

分支rebuild-v1-protocol-20260915；实验基准1a8a840，A工具961c719，GPU吞吐探针526d5a0。用户终端执行，本地无服务器直连。

研究仍是可行性探索：优先频率＋语义可靠性、模态退化/缺失训练与推理；C1旁支，部分解冻强基线，允许换解法/交叉问题/方向。章节和贡献未冻结。见[决策](RESEARCH_DECISION.md)。

D23-A最后带时钟观测2026-10-01T12:44:35.075903+08:00 COMPLETE：Potsdam Val2、R0/M0 seed42 final16000、NoBoundary fg5，标签选择诊断clean +1.592737/rgb_down4 +2.415542/noise +1.657089pp，平均+1.888456pp，通过准备B投入条件。不是learned gate、语义或频率成立证据。原件仍服务器；A轻量归档报告SHA041bc0ad79c3c5f11fdbf4a29479b2c3cf68d60f898b5125d8cf2211e59084b1，尚未收到本地。不重跑A。

最新用户回传：17be568两卡数值诊断均执行结束（结束时钟未给）。两卡统计/SHA相同，micro2/4/8在该批裁剪上logit完全相同；micro16有少量可重复判定差异；所有固定微批两次预测均稳定。原件仍服务器，见[双卡诊断结果](../experiments/D23_B_DECISION_AUDIT_RESULTS_20261001.md)。原短测/诊断均保留，目录records/research_d23_b_decision_audit_20261001T132944_658274；主机内存/磁盘充足、两卡H100为用户声明，运行时仍核对空闲。

B核心及完整入口已实现，详情见下方本轮更新；当前专家micro8、gate batch16、单次backward，服务器新路径验收待执行。

训练/14条件整图评价入口、TCAP fit统计、样本流、滑窗拼接后回退代码已实现；服务器完整验收、整图与双卡资源预算待完成，正式8组4000步队列未启动。原收益/风险/机制门槛保持；频率无独立增量撤回其贡献，gate无收益关闭解法，不自动补seed或调阈值。见[下一实验](NEXT_EXPERIMENT.md)。

旧Test6已历史暴露，禁读且无独立final资格；Post-D21原摘要等归档缺口仍存在。第一轮光学可用、已知DSM mask回退；未知缺失、光学全缺失与独立来源泛化仍未验证。

全部服务器快照/日志/JSON/归档保存在/home/jovyan/zzx下的对应实验目录；新诊断目录records/research_d23_b_decision_audit_<timestamp>_<pid>。不覆盖或移动原产物。上一交接见固定526d5a0版本。


## 本轮入口实现更新（2026-10-01）

用户说明H100为80GB并询问累积必要性。本轮改为专家micro8提取/缓存detach证据、gate batch16、两视图loss一次backward，取消gate累积；该实现未GPU实测，新吞吐不能沿用旧0.308秒/步。8组有效batch/样本流/预算与研究门槛保持。

run_rebuild_v1_d23.py/d23_engine.py/d23_lifecycle.py/summarize_rebuild_v1_d23.py已实现：固定样本键、训练数据磁盘缓存、formal TCAP256裁剪/12tile统计、最后4000步checkpoint/resume、14条件整图Full/NoBoundary计数/pooled与harm/rescue、后拼接缺失回退和八组screen。代码已实现≠服务器已验证；新22项本地CPU合成测试通过，服务器完整流程尚待验收。正式runtime lock与自动8组队列未生成，formal模式拒绝无实测预算锁。

立即动作改为GPU0 smoke、GPU1 profile顺序工程验收，每任务30分钟外层超时；smoke仅训练tile2_12 8组各2步/768图14条件，profile同tile TSF12步/整图3条件。全部结果在zzx项目records/research_d23_b_engine_admission_<timestamp>_<pid>，禁读Val2/Test6，无正式训练。见[执行范围](../protocols/D23_B_ENGINE_ADMISSION_20261001.md)。旧single micro8×2仅历史选择，不再是当前gate反传方式。
