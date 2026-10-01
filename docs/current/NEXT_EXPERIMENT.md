# 下一步：在服务器nohup启动D24十五组

更新2026-10-01 23:57:09。用户已明确“按计划进行吧”。[15组科学协议](../protocols/D24_OVERNIGHT_MULTIPERSPECTIVE_20261001.md)及代码全部实现，15项本地CPU必要检查PASS；[执行说明](../protocols/D24_OVERNIGHT_EXECUTION_20261001.md)包含启动、进度、恢复和轻量上传命令。无新增服务器运行观测，不能称已经启动。

直接从固定执行提交导出standalone launcher，nohup运行；GPU0先A0，GPU1先A2。两H10080GB、内存/磁盘充足已确认，不跑资源/预算探针，不再征询这些已知条件。正式首步验证新梯度范围，8线程准备物理batch16，无梯度累积。4000步/组，合计60000；每job最多6h，失败留证并继续其他任务，不能把技术失败当科学负结果。

全部产物在records/research_d24_overnight_<timestamp>_<pid>，属于/home/jovyan/zzx；D23目录保留不动。主Git工作副本只fetch，不checkout/reset。控制器锁与job锁防重复；断线不会终止nohup/独立worker，确需恢复时同一目录和同一执行提交，已完成组跳过、未完成同绑定checkpoint/RNG恢复。

完成后自动screen_result/results.csv，手动终端运行uploader以便凭据交互，长输出直接GitHub读取。评价原计数/配置/绑定/轻量日志上传；模型/预测仍在服务器并索引。Val2选checkpoint，Test6禁读；C按光学能力比较，普通增强/更新单独判断，最多两条筛选通过假设另立确认，不自动开多种子。

[当前交接](HANDOFF.md)、[机器计划](../../records/research_d24_overnight_plan_20261001/plan.json)、[本地检查记录](../../records/research_d24_overnight_plan_20261001/local_validation.json)。
