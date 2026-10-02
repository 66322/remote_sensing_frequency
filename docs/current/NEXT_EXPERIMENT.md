# 下一步：一次启动已授权D25八组

更新2026-10-02。用户已授权具体执行，八组已实现、12本地CPU行为检查PASS；固定执行提交0c31167d0fdb57f03459ea18981c1ee02bcee9f2，服务器启动观测待回传。

直接按[D25执行说明](../protocols/D25_EXECUTION_20261002.md)一次nohup启动。GPU0/1双H10080GB、RAM/硬盘充足、batch16不累积、8×4000沿用；不再重做资源/预算/长smoke。全部产物在新zzx/D25目录，不重启D24。

记录实际D25_DIRECTORY/PID/首步时间；后续查询同一个目录。科学对照和去留条件按[协议](../protocols/D25_MISSINGNESS_OPTIMIZATION_PLAN_20261002.md)冻结，自动汇总完整/缺失、原计数及梯度诊断，压力条件不选模/选赢家。完成或失败后运行snapshot uploader把原件写回同一GitHub分支，长输出由链接读取，预测/权重留服务器。

授权仅固定八组，不自动加seed/lambda/步数、安装依赖或访问Test6。无实时服务器连接，运行态注明实际最后观测。
