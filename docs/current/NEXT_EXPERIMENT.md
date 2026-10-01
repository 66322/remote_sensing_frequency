# 下一步：nohup接续剩余六组

更新2026-10-01；共享分支rebuild-v1-protocol-20260915。原证据提交9a70648affe105367e1b6e42ac4919f66140d7aa；目录records/research_d23_b_formal_20261001T152548_658274/evidence_20261001T175246424862_812335。最后队列观测2026-10-01T16:35:53.227191+08:00为TECHNICAL_FAILURE；用户随后报告两卡闲置，不是助手实时服务器观测。

TSF于16:34:33、T0于16:35:51由controller记录COMPLETE，日志均有4000步和两tile×14条件评价完成。TS启动退出码2，唯一错误为requested physical GPU is busy; no job is interrupted；没有正式训练/评价完成记录。TF/TCAP/TSF_CE/shuffleS/shuffleF未启动，screen_result不存在。当前是2/8完成，不能写成全队列完成、机制成立或全部验收通过。

研究仍是频率＋语义可靠性对RGB–DSM退化/缺失融合的可行性探索；C1旁支、部分解冻强基线；角色和冻结阈值不变。Test6禁读，Potsdam Val2为开发证据。

本轮修复仅修改controller：每次启动前等待目标GPU与锁定UUID一致，连续两次满足原空闲条件，最长90秒；显示显存、利用率和compute PID。现有日志不能区分历史采样延迟与真实占用，不能声称确定根因。等待超时保留错误，不终止别人任务。保留被跳过的完成组元数据/日志链接；模型、训练入口、engine、lifecycle、probe、runtime lock均未修改。10项本地模拟检查通过，服务器修复执行尚未观测。

下一步：用新controller在原目录nohup --resume-queue接续，仅补TS/TF/TCAP/TSF_CE/TSF_shuffleS/TSF_shuffleF六组，跳过TSF/T0，原失败日志/结果保留。GPU0/1两张H10080GB、主机内存/磁盘充足，所有记录在zzx对应目录。无需再跑smoke/预算。每组4000步、专家micro8、gate16、单backward及各项风险/机制门槛继续沿冻结协议。完成后前台上传轻量原件，再进行八组比较。

接续命令在本次回复中给出，执行快照固定新controller提交；不要手工改runtime lock或重新运行TSF/T0。接续后应首先出现GPU0 TS、GPU1 TF进程启动；后台日志保存在本次目录。提速prefetch开发仍在本地未发布，不混入本轮对照。
