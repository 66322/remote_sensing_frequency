# 新对话承接

继续66322/remote_sensing_frequency，rebuild-v1-protocol-20260915，以GitHub为准。先读START_HERE及研究决定、HANDOFF、PROJECT_STATUS、NEXT_EXPERIMENT和实验整理。

最后服务器观测：2026-10-04T17:21:47.568226+08:00（用户终端查询回传），Post-D30为RUNNING，控制器2720259 LIVE=True，主体12/18完成：A0—A5、B1—B6全部COMPLETE；C0在GPU0训练3760/8000步，C1在GPU1训练3780/8000步，两worker PID_LIVE=True；C2—C5 PENDING，F0—F3仍有条件。原队列已进入C，禁止重复恢复或新建队列。旧08:12日志的model导入错误仅作历史记录。本次仍未收到上传提交，GitHub没有新增A/B原生结果；固定A2/B3门槛尚待原件分析，不能由技术完成判定科学成立。

主线RGB–DSM双向条件互补与退化/缺失分割；任务驱动恢复是旁支，仍在可行性探索，没有确认性新贡献。D23—D30失败配方不重跑，不自动加seed。A2固定主候选，A4/A5敏感性；B3固定gate决定F；C2对原教师/硬标签对照。上传阶段原件后分析A，原C沿原控制器继续，不再恢复或另建队列。

用户终端操作无SSH；GPU0/1两张H10080GB，nohup、seed42、8000步、batch16无累积，全部记录/缓存/快照在zzx对应实验目录。资源充足不重复审计，不访问Test6/独立final。重要记录继续同步同一GitHub分支并核验。
