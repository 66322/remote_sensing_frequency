# Phase3-M1：重启中断，恢复包待服务器启动（2026-10-15）

用户16:26:47回传确认原run `research_phase3_m1_20261015T143433_2657574` 无本实验存活进程，GPU0/1空闲；旧状态文件16:03的RUNNING是残留。原7组完成标记和端点文件存在，共112000次更新。恢复注册会实际核验SHA，不将“文件存在”当作完整性已确认。

已完成：M10/42、M10/17、M11/42、M11/17、M20/42、M21/42、M21/17。中断：M20/17最后12520步、M01/42最后2680步，有滚动checkpoint，预计12k/2k，实际以checkpoint内部step为准。未开始：M01/17、M00/17。

下一步：用本恢复提交固定SHA执行 `scripts/recover_phase3_m1.py --directory /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m1_20261015T143433_2657574 --commit <恢复提交完整SHA>`，整段注册放入nohup。不是重新执行原bootstrap，不把原queue_status改回REGISTERED。

新run保持原目录不改写，7完成组保留原绑定并以逐文件SHA桥接；中断组恢复模型、AdamW、CPU/CUDA随机状态和原样本位置，并回滚日志到已提交step。主训练剩余预计50k有效更新；重建丢失的匿名RAM预测。已有门禁若落盘，重算须一致。科学方案、16k端点、batch16、GPU0/1及sealed splits不变。

[恢复协议](../protocols/PHASE3_M1_REBOOT_RECOVERY_20261015.md)；[检查记录](../../records/phase3_m1_reboot_recovery_review_20261015.json)。实际H100恢复及后续结果尚无回执。

已实现注册锁、原控制器锁、无活跃本实验进程及GPU占用核对，重复命令只显示已有恢复目录。没有tmux操作或向其他任务发信号。缓存清理仅限新run自身的运行缓存、临时文件和成功后的滚动优化器；原中断记录暂作恢复来源保留。
