# 新对话承接

继续66322/remote_sensing_frequency，rebuild-v1-protocol-20260915，以GitHub为准。先读START_HERE及研究决定、HANDOFF、PROJECT_STATUS、NEXT_EXPERIMENT和实验整理。

最后服务器观测：2026-10-04T12:05:36.507045+08:00（用户终端查询回传），Post-D30为RUNNING，控制器2720259 LIVE=True，主体8/18完成：A0—A5与B1/B2 COMPLETE；B4在GPU0训练5940/8000步，B3在GPU1训练4000/8000步，两worker PID_LIVE=True；B5/B6及C0—C5 PENDING，F0—F3仍有条件。第二次汇总修复已恢复原队列并进入B，无需重复启动。旧08:12日志的model导入错误仅作历史记录。A原生结果及修复manifest仍待上传核验，不能由运行恢复推断科学门槛通过。

主线RGB–DSM双向条件互补与退化/缺失分割；任务驱动恢复是旁支，仍在可行性探索，没有确认性新贡献。D23—D30失败配方不重跑，不自动加seed。A2固定主候选，A4/A5敏感性；B3固定gate决定F；C2对原教师/硬标签对照。上传阶段原件后分析A，原B/C沿原控制器继续，不再恢复或另建队列。

用户终端操作无SSH；GPU0/1两张H10080GB，nohup、seed42、8000步、batch16无累积，全部记录/缓存/快照在zzx对应实验目录。资源充足不重复审计，不访问Test6/独立final。重要记录继续同步同一GitHub分支并核验。
