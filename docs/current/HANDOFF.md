# 当前交接：首批全部完成，按新回执复盘（2026-10-30）

先读[研究决定](RESEARCH_DECISION.md)、[状态](PROJECT_STATUS.md)、[下一步](NEXT_EXPERIMENT.md)、[阶段复盘](../experiments/POST_M2_FIRST_WAVE_COMPLETION_REVIEW_20261030.md)。前版进度归档见[历史](../history/HANDOFF_BEFORE_COMPLETION_RECEIPT_20261030.md)。

## 决定、角色与下一不确定性

用户指出已具体安排且两卡停止，要求按GitHub核对。本轮读取最新头870ecff并结合完整粘贴回执，修正过期的“尚未实施/分数待收”判断。主线未切换，当前为第一轮完成后的诊断阶段。G/Q具体实现收缩；S正确对应有弱正线索但未过门槛，不能写成已成立贡献。A未验证整体DINOv3稳定优势。未采纳自动重跑、扩seed、直接组合或倒改门槛。

下一步只读接收Full逐tile/边界计数、端点/学习轨迹及空间逐tile，解释S/G/Q机制和类别差异；不再启动任何首批入口，不因上传缺认证重算。

## 最后完成回执

ROOT=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro。
- Full run records/post_m2_multiroute_v2_20261030_r1，冻结d15f34e8d53f935aa17542123c2227fab14cb810；20:06:07+08，11×8k完成，blocked/partial空，共88k。
- 空间run records/post_m2_a_spatial_followup_20261030_r1，执行5f2958ae8b7d3ac79901eb0261239d89e82b461e；20:39:39+08两头各2k及全部阶段完成；resident两模型各加载一次、训练缓存已释放，worker release返回−15与完成后回收一致。
- 原A0 run records/post_m2_a0_ipcfix_20261030，科学c22、IPC执行d15，两线性头各2k及完整评价已验。
- 合计15项/96k正式更新；profile另计。最后GPU空闲快照20:37:49，后有空间工作和20:39:39释放；不能写为实时资源盘点。

## 已收科学结果与验收边界

Full G主差+0.3440pp、最差tile−1.2208pp且不胜错配；Q主差−0.0832pp且不胜时序控制；S边界F1+0.3778pp、对应差+2.0992pp、clean mIoU+0.1965pp。三组SPECIFIC_IMPLEMENTATION_NOT_PASSED，不扩大为问题不成立。

空间NB128内D2/D3=75.2788/73.9589，外=73.7043/70.4069；四pooled 6×6矩阵、support和总像素重算相符。原线性内READY、空间READY_SPATIAL_OUTER资格均保留。Full512分数与A组NB128不混比。

来源为[用户粘贴转录](../../records/post_m2_completion_receipt_20261030/user_pasted_receipt.json)；助手没有SSH。Full逐tile/边界原件和空间逐tile尚未接收，不能称全部原始科学计数独立验收。小转录同步GitHub不代表服务器全量归档已上传。两空间端点head_2000.pt各80429 bytes仍在服务器，未上传；本次不删除。

A1/A2、C/P/E/F、频率仍未入队，默认42未扩种子。Val2/Test6/held4/final关闭。M2最终清理仍暂缓、最后18端点，J工程停止；本次均不重启或恢复。GitHub为两电脑权威，后续按新current接续。
