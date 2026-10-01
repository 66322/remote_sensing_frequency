# 下一步：运行双卡资源测量，结果直接上GitHub

[执行方案](../protocols/D23_B_DUAL_GPU_BUDGET_20261001.md)已实现，本地27项CPU检查通过。入口scripts/launch_rebuild_v1_d23_budget.py，实际服务器预算未运行。

1. 从固定提交提取launch入口到新的zzx对应实验目录，GPU0/1空闲时执行。controller先跑CPU检查，再同时测两卡12tile缓存、256个TCAP样本、八组各16步和训练tile14条件整图评价。每卡30分钟限制，失败保留记录并停止另一worker。
2. 完成后自动将13份轻量原件和1份manifest上传同一GitHub分支。用户仅回复提交号；不再次粘贴长JSON。大型缓存/预测/权重留本次服务器目录。
3. 助手复核绑定、两卡固定预测一致性、缓存/统计/整图预算与数据读取成本；估计中的NoBoundary/Val2读取余量单独报告。结果只为BUDGET_MEASURED_REVIEW_REQUIRED，不自动准入正式训练。
4. 满足工程预算后冻结源码/backend/输入绑定及runtime lock，准备8组各4000步固定final screen。研究阈值、8组/6固定/14条件不变，Test6禁读；工程成功不等于门控/频率贡献成立。

此前双卡工程验收已完成，[GitHub原件审计](../experiments/D23_B_ENGINE_GITHUB_AUDIT_20261001.md)，不再重跑。
