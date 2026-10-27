# 当前交接：M2 101/108，完整条件评价仍在途（2026-10-27）

## 最后观测与证据

用户终端最后观测 **2026-10-27 20:00:23+08:00**：[原始输出的轻量分析](../experiments/PHASE3_M2_PROGRESS_20261027T200023.md)。M2 `RUNNING`，101/108训练完成、失败/阻断0；GPU0/1分别在训练F2_s2026_DShuffle、F2_s2026_DEntropy，两个控制器及两计算进程当时可见。完整条件评价累计2667个case，状态仍报F0/tile 6_7/`rgb_fault`，源码已核对总量77,868例，计数覆盖3.425%（不是耗时完成率）；M2 summary/gates尚未生成。合并`WAIT_M2`，J/R/T/V尚未开始。这是历史快照，不能外推为当前实时进程状态，也没有执行停止脚本。

只读中期表有101行合格：F0、F1训练各36/36，F2为29/36。8组已合格的fold×seed配对中，目标DF的clean DSM-only nb fg5均低于D0，且低于DSelf；DSelf相对D0为6正2负。该跨外折单模态信号提示DF的clean精度保护风险，尚无RGB-down4补救、损伤、固定融合、换配和未见退化的完整联合计数，**不能判G1–G4或把具体DF配方问题扩大为研究问题失败**。端点字节、整数矩阵与训练轨迹仍待最终独立核验。

## 研究角色与下一步

主线仍是RGB–DSM双向条件互补与退化/缺失分割，恢复旁支；[研究决定](../current/RESEARCH_DECISION.md)和[阶段复盘流程](../protocols/ITERATIVE_RESEARCH_REVIEW_20261025.md)不变。连续建筑地图维护仍是独立优先候选，尚未数据验包、实现或训练，也未入当前队列。现有M2→J→R→T→V上限228个作业；M2须108个端点和联合计数完整性G0验收后才可能进入J/R。T/V另需公开数据catalog；B/C未开放，test封存。

下一关键证据是首折完整条件面板与M2最终summary/gates。继续只读查看原目录，不重复bootstrap/repair、改环境、重启或补seed。若遇实际失败，保留首栈与原件，不自动重跑；若用户主动释放GPU，按[本次专用中断协议](../protocols/PHASE3_M2_INTERRUPTION_AND_GPU_RELEASE_20261025.md)核验归属后终止，不能把它当可恢复暂停。当前无服务器停止或续跑回执。结束后核验端点/SHA、原始int64计数、样本流、训练轨迹，再判科学门禁、轻量同步和下一实验。

当前M2目录：`/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m2_revision_20261024T092814_2738345`；合并目录：同一records下`research_phase3_combined_revision_20261024T092814_2738345`。科学源M2 `ac325cdbb403ebb95b5eb0acbf17fffa5441dcfd`，合并`e65c6cb0830985461b3cd30e2f43158dd3d858cb`；工程修订`752d3835a18a15a04d83b1dcc1841bff98bf0b07`、`25b124a0cf69ececb6841b55ed90b19fae5b9a08`；只读读取器`624194105b3b018bb1e1e66d80cada2a405e7758`。服务器仅由用户操作，无SSH。

[前一版交接归档](../history/HANDOFF_20261027_BEFORE_101_UPDATE.md)；[稳定入口](../current/NEW_CHAT_HANDOFF.md)、[查看指南](../protocols/PHASE3_PROGRESS_AND_RESULTS.md)、[启动故障长期规则](../protocols/STARTUP_DELIVERY_AND_FAILURE_CONTROL.md)。
