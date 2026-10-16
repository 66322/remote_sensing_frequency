# 新对话直接接续：Phase3-M1执行包就绪（2026-10-15）

Phase3-M1已按用户要求落实执行包，尚未取得服务器启动回执。仅使用本篇遥感RGB/DSM/标签，GPU0/1，固定16k、batch16；11个新主训练，最多2个条件反证，总上限13个新训练208k更新。旧M00/42在绑定合格时复用，Test6/held4/final不读，点云论文不进入本轮。

双卡共享就绪队列，空闲卡可以领取另一seed任务。GPU到CPU交接只等内存接收，不等计数完成；RGB故障前向跨所有DSM对照共享。Fit训练RAM在全部训练消费者结束后分进程释放，条件预测匿名RAM在最后计数消费者结束后关闭，成功作业的滚动优化器在端点与主计数核验后退役。GPU无后续任务时先退出，CPU继续收尾；所有自有进程退出后清理runtime cache/temporary。负结果、失败恢复状态、必要16k权重和充分整数证据保留。

[执行与清理协议](../protocols/PHASE3_M1_EXECUTION_20261015.md)；[科学设计](../protocols/PHASE3_M1_DESIGN_20261015.md)；[包清单](../../configs/phase3_m1_execution_manifest.json)；[本机检查记录](../../records/phase3_m1_implementation_review_20261015.json)。

固定执行包已实现；不要重复从设计写代码或重做全部检查。唯一下一步是服务器执行不可变提交的bootstrap并读取真实launch/queue状态。暂无新run/PID/训练结果；不把代码就绪写成运行中。原GPU资源与清理授权持续有效，不再询问同一事项。旧实验、tmux/Git排错和上传已经收尾。
