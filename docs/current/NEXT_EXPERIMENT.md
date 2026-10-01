# 下一步：定位恢复收益的逐 tile 风险

原 42 项与后续 4 项均已完成，见[结果报告](../experiments/POST_D21_FINAL_AND_MIXED_FOLLOWUP_RESULTS_20261001.md)。当前不再启动训练。先检查混合退化 C0/C1 的逐 tile 整数矩阵与逐类 IoU，重点是 Vaihingen tile20（×2 clean −0.815 pp）、tile33（×2 未见模糊 −1.421 pp）和 Potsdam `5_10`（×2 未见模糊 −0.209 pp）；结合边界与恢复诊断辨别损失来源。

若局部风险可以解释且预设保护可通过，再规划同起点、同预算的必要成对复验；外部地区数据需先独立验收并说明获取路线。不得用 Test6、补第三种子或开发集反复调参消除既有失败门槛。用户贴出的紧凑分析已经归档，完整评价产物仍在服务器；上一版下一步见[历史](../history/20261001_before_final_post_d21_results/NEXT_EXPERIMENT.md)。
