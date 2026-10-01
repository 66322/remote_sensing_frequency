# 下一步：D23-B实现与预检准备

D23-A已满足准备门槛，见[A结果](../experiments/D23_A_COMPLEMENTARITY_RESULTS_20261001.md)：三条件平均互补空间1.888456pp。B核心已实现、本地CPU8测试PASS，完整训练/评价入口尚未实现，正式训练未启动。研究定位仍见[决策](RESEARCH_DECISION.md)。

1. 补A原始profile/decision/10tile-condition JSON与日志轻量归档，不重跑A。
2. 用户服务器CPU复验tests/test_d23_gate.py已PASS（8项/1.732秒），下一步实际DINO/训练crop GPU短测；[B准备记录](../protocols/D23_B_IMPLEMENTATION_PREPARATION_20261001.md)。
3. 完成单一fit采样、TCAP fit统计、有效batch损失分母、4000步训练与14条件整图评价入口；真实D21冻结专家128通道hook、前向一致性与滑窗后缺失精确回退核对；保持原8组/6固定比较与门槛。
4. 先执行[训练crop短测](../protocols/D23_B_CROP_GPU_PROBE_20261001.md)，冻结专家、单GPU、4组各12短测步，不保存权重；再按[完整协议](../protocols/D23_DENSE_BENEFIT_FEASIBILITY_20261001.md)完成已分配单GPU有界短测，测真实吞吐/RSS/显存/磁盘并冻结wall/job cap，才生成正式队列命令。不从CPU A的两分钟外推B工时，不复用旧授权假定GPU空闲。

A的label-informed互补诊断不能部署，不能当频率/语义/gate成立；B无增量关闭此解法，频率无独立增量撤回相应贡献。继续/换解法/换问题均按证据判断，C1不自动升级。旧Test6历史暴露，禁止读取，独立final资格另以独立来源建立。
