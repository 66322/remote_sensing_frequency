# 下一步：读M2完整条件面板并复盘机制（2026-10-27）

1. 最后服务器观测 **2026-10-27 20:00:23+08:00**：M2 `RUNNING`，101/108项训练完成、失败0，两张GPU各有一项训练；完整条件评价计2667/77868例，计数覆盖约3.4%（不是耗时完成率），summary/gates未生成。合并`WAIT_M2`，J/R/T/V未开始。[本次中期证据](../experiments/PHASE3_M2_PROGRESS_20261027T200023.md)。这是最后观测，不是实时状态；此前45/108和51小时外推已过期。
2. 只读复用服务器已有`records/phase3_engineering_restart_package_752d3835a18a15a04d83b1dcc1841bff98bf0b07/scripts/status_phase3_engineering_restart.py --tail 20`，按[查看指南](../protocols/PHASE3_PROGRESS_AND_RESULTS.md)核对进度、失败、首折条件面板与最终结果。不再启动、重复修复或下载启动包。
3. 当前clean DSM-only的八组配对中DF均低于D0且低于DSelf，属于精度保护风险预警；不能用它判RGB-down4补救、融合或G1–G4。优先取得完整联合整数计数与固定融合结果，依预定H1/H2、G0–G4区分对应性、普通自身难例、分层打乱/熵、DMix等简单解释。F2 seed2026仍缺D0配对，不把NA当零或负结果。
4. M2阶段完成后先验108端点及SHA、数据/teacher与配对样本流、int64矩阵、逐tile结果、训练轨迹和工程修订，再解释门禁并同步轻量记录。若实际失败先保留首栈，不自动重跑或加种子。G0完整性通过才可进入J/R；T/V另需公开数据catalog，缺失时等待。B/C与Test6/held4/final均不开放。
5. 如果用户主动释放GPU0/1，按[当前中断协议](../protocols/PHASE3_M2_INTERRUPTION_AND_GPU_RELEASE_20261025.md)先核验归属再终止。当前没有安全暂停或自动断点续跑；停止后须审计已完成作业与在途评价，另建版本化续跑合同，不删除回执、不直接重启旧目录。本次只读回执没有执行停止命令。

研究推进按[阶段证据复盘](../protocols/ITERATIVE_RESEARCH_REVIEW_20261025.md)：每有完整配对结果，先回答原问题、最强简单解释及未回答部分，再决定保留、收缩、换解法或试新方向。主线仍是RGB–DSM条件互补；独立[连续建筑地图维护](../experiments/INDEPENDENT_RESEARCH_ROUTE_20261023.md)先公开数据验包、冻结月度/AOI/标签合同，再实现独立重建与递归基线、简单滤波和重置。拟议首阶段seed42×两基线×三个地理划分尚未入队，不占当前GPU。

新计划先遵守[实验规划规范](../protocols/EXPERIMENT_PLANNING_RULES.md)：探索默认单seed，必要重复通常先42/17；第三须说明两者不足的问题与额外成本。低GPU利用率须以真实训练/评价分段证据定位；未修改冻结队列或完成目标profiling。[启动交付规则](../protocols/STARTUP_DELIVERY_AND_FAILURE_CONTROL.md)持续有效。
