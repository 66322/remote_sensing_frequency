# 下一步：在服务器一次nohup启动D27后接controller

用户已授权新实验接在D26后。代码/固定plan实现完成，14CPU行为、30文件独立快照、11文件Python3.10语法与五入口检查通过。没有SSH，服务器排队/运行尚未观测。

使用本次固定执行commit提取scripts/launch_rebuild_v1_d27.py；--parent=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d26_bidirectional_20261002T191253_1513109；
--directory=/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_d27_safe_routing_after_d26_20261002T191253_1513109。
详见[执行说明](../protocols/D27_SAFE_ROUTING_EXECUTION_20261002.md)。

一次后台启动后，D27_WAITING_D26为正常状态；原队列完成并退出后自动开始G0/G1及其余组。两卡独立动态领取十组，每组8000，不扩大预算。不得重复nohup创建第二个同任务目录。

状态查询：新目录code/scripts/status_rebuild_v1_d27.py --directory新目录；日志nohup_<stamp>.log及各job logs。完成后用新目录code/scripts/upload_rebuild_v1_d27_records.py上传轻量原件，无需聊天粘长输出。代码、JSON/矩阵/联合计数写GitHub，weights/预测服务器留索引。

最后上传的服务器观测仍为2026-10-02T22:22:14.689169+08:00：D26 RUNNING、COMPLETE1/9；没有更新实时PID信息。 原D26最终结果仍按原门槛判定，不用新D27规则改旧结论。新实验安全、路由、局部、类别各有匹配对照和独立去留，最多一条另立确认；不自动追训/扫参/Test6。GPU0/1两H100、内存磁盘充足、batch16、nohup、zzx边界不再询问或审计。
