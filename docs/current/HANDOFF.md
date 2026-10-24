# 当前交接：M2双GPU真实训练更新已确认（2026-10-24）

最后服务器观测2026-10-24 09:54:39+08:00：M2为RUNNING，输入12/12已于09:49:45完成；GPU0的F0_s42_T3推进到2600/32000，GPU1的F0_s42_T1推进到2620/32000。两个控制器2754693/2754694存活，作业失败0、完成端点0；合并WAIT_M2为正常依赖等待。此为最后观测，不是实时状态。

[最新训练证据与用户终端副本](../experiments/PHASE3_REVISION_TRAINING_STARTED_20261024.md)。GPU worker为2757402/2757403，各约3728MiB进程显存。M2_TRAIN包含1、500、1000、1500、2000、2500次更新，最新progress为2600/2620；不能以启动器Done替代训练证据，本次已有实际更新。当前T1/T3是M2内层OOF教师，不是后续3DCD的T阶段。

M2目录：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m2_revision_20261024T092814_2738345。
合并目录：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_combined_revision_20261024T092814_2738345。
全局单次回执records/phase3_engineering_restart_20261024_once.json为CONTROLLERS_LAUNCHED。基线752d3835a18a15a04d83b1dcc1841bff98bf0b07与额外路径25b124a0cf69ececb6841b55ed90b19fae5b9a08分别绑定，旧失败及原目录保留。补丁8项、原M2全16项及合并11项通过的目标回执见前一阶段记录。

继续现有队列；用户按需只读运行status_phase3_engineering_restart.py --tail 40。下一关键证据是8k/16k/24k/32k轨迹及首个完整32k端点，最终仍须核验全部原始整数计数、端点与轻量原件。若出现FAILED/STOPPED或进度不再推进，读取新证据诊断，不自动重跑。不再bootstrap、repair --apply、删除回执或重启。

xFormers处于禁用回退分支，警告未阻断本次实际更新，不据此安装依赖或改环境。GPU31%仅为瞬时采样，不据此改预算或并行策略；count_workers=32为配置，当前cpu_tasks=0。ps ELAPSED异常，不用于估算时长。现有loss不是分割性能结论，尚无完成端点或科学门禁通过结论。

研究阶段、主线与独立候选角色保持；M2→J→R→T→V原预算/种子/科学门禁不变，B/C不开放，后段缺数据WAIT_PUBLIC_DATA。test封存、GPU0/1、有界内存、用户执行服务器命令无SSH保持。原始材料尚未全量取回；结束额外验收路径补丁和752d runtime材料。前一交接见[归档](../history/HANDOFF_20261024_BEFORE_FIRST_TRAINING_UPDATES.md)。