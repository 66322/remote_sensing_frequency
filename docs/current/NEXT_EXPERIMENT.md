# 下一步：沿GPU0恢复任务继续，勿重复启动

## 最新恢复启动观测（2026-10-01用户回传）

48ab1e4恢复入口已由用户nohup执行。恢复controller PID834840；GPU0空闲短等待通过，随后D23_RECOVERY_TS_STARTED，TS PID834884。当前只确认进程创建，尚未取得恢复后训练step或完成记录。没有独立回传墙钟；以下文件名中的18:37:00是启动标识，不作为实时存活保证。

恢复controller日志：/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d23_b_formal_20261001T152548_658274/nohup_recover_gpu0_20261001T183700_834385.log
TS直接日志：同目录/TS_gpu0repair_20261001T183700466561.log

下一步沿此恢复任务继续，不再次启动。TF保留由旧controller管理，其当前进度未新观测；恢复入口在TS与TF完成且旧controller退出后自动接续剩余四组。需查看训练步骤时只读TS直接日志；结束后按后台提示前台上传轻量原件。此前“恢复尚未执行”的表述现为历史背景，不覆盖本节。


资源、科学协议和完成TSF/T0均沿用；没有部署prefetch或新增资源审计。只读最新日志，不用旧PID或陈旧输出断言实时状态。

最新用户回传（2026-10-01，无独立观测墙钟）：TS_gpu0repair日志已出现D23_GATE_TRAIN TS 1 1.0572699308395386，确认恢复后已执行训练step1。此前“训练步骤尚未取得”是旧观测；TF当前进度未新回传。新增只读查询scripts/status_rebuild_v1_d23.py，覆盖旧队列及GPU0恢复任务，并按既有实际耗时估算ETA。[进度查询说明](../protocols/D23_PROGRESS_QUERY_20261001.md)。
