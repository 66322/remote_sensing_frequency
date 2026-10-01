# 下一步：启动八组正式开发对照

预算已完成并从GitHub核验，不再测量资源。已交付scripts/launch_rebuild_v1_d23_formal.py与现有formal接口runtime lock，新增5项队列模拟检查通过。当前没有正式训练已启动证据。

用户从固定提交提取入口到新的zzx/research_d23_b_formal目录，GPU0/1执行四轮8组各4000步；开始即正式训练，不再跑smoke/probe或CPU重复验收。目的、预算、停止条件与完整[执行方案](../protocols/D23_B_FORMAL_SCREEN_EXECUTION_20261001.md)已记录。原骨干/数据划分/退化/keyed样本/seed42与研究阈值不变。

两卡各四组，单组预算8519秒，队列保守约9.5小时；每job3小时hard wall。固定final checkpoint后评价Val23_11/5_10×14条件，6固定与该组，保存Full/NoBoundary原整数计数。全部完成才冻结screen结论，不能从中途精度加任务/改方向。

每30秒显示组名、耗时与最新日志，技术失败停止新任务并保留当前另一卡工作。完成或worker技术失败后，将明确轻量JSON/日志上传同一GitHub分支，预测/缓存/checkpoint留服务器。用户只回传提交号。助手回读后判断门控、独立语义/频率增量和缺失/退化风险；工程成功不等于贡献成立，Test6继续禁读。
