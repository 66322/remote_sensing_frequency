# 项目状态：N3/S1已验收，GPU0后续方案仅规划

最后服务器查询（用户终端）：2026-10-08T22:11:10.555448+08:00；queue最后观测2026-10-08T06:37:48.607436+08:00，N3_S1_COMPLETE_AWAITING_REVIEW。九组全部COMPLETE/8000，查询时controller/worker LIVE=False。本次只做规划，没有新的服务器运行观测。

前置[完整结果](../experiments/POST_N3_S1_RESULTS_20261008.md)已独立验收，原件38d205591abe00179bebfb36a17595d4d7b75f47，验收提交4163107e55bc560a8ba83784e3759caa3a4a299b。N3固定候选相对局部−0.000078pp、相对网格+0.001937pp，关闭该区域配方的增量承诺。S1-3 RGB局部U对S1-0 +4.102047pp，两tile正；DSM −0.023201pp且tile异号；aux_shift8/3_11 −0.391546pp违反原−0.2pp保护线。两旧gate维持False，S1是单向收益与退化代价的开发线索。

验收范围：1508载荷+manifest路径/大小核对，79选定JSON+manifest回读，227556矩阵、22140原joint边际/池化、1044case、9396预测索引绑定；12科学源/协议与执行0e22438逐字一致。未回读全部原件或服务器数组/权重/mask本体，未GPU复跑，joint_reports派生字段未穷举复算。

|阶段|状态|去留|
|---|---|---|
|N3五组|已完成/已验收|固定区域配方增量不足，关闭|
|S1四组|已完成/已验收|单向收益，保护失败，保留线索|
|D0/D1|仅规划、0新训练|区分位置/推理/参数效应|
|P0—P9|仅规划、10组、新8000各|GPU0串行，P7预先固定|
|E|仅规划、6条件|检验形状与DSM质量边界|
|Q0—Q3|条件储备、未实现|无足够DSM证据不触发|

新[Post-S1单卡规划](../protocols/POST_S1_SUPPORT_GPU0_PLAN_20261008.md)为PLANNED_NOT_IMPLEMENTED_NOT_REGISTERED：D0复用预测＋D1权重/策略诊断→P十组（2×2×2配对＋2机制控制）→E六压力条件；Q四组仅条件储备。约33—57h首轮单卡预算，首个隔离/共享作业后校准，无科学总时间上限。新代码、可运行入口、队列和PID均未建立，不能运行旧双卡enqueue。

研究阶段仍为可行性探索，主线RGB–DSM条件互补与退化/缺失分割，恢复旁支。Potsdam fit12/Val2=3_11、5_10、native512/stride256、NoBoundary fg5主/Full诊断、seed42；两Val tile反复开发，不宣称独立泛化/显著性。N5/N2/C旧配方去留保持，R1/N4/R2不自动激活。

用户2026-10-08最新指令：本轮只能物理GPU0，覆盖诊断、测试、推理、训练及恢复，physical_gpus=[0]、CUDA_VISIBLE_DEVICES=0，单worker串行；GPU1不得使用。旧记录中的GPU0/1仅为历史。服务器由用户终端执行，无SSH；nohup，全部记录/快照/缓存/临时文件在zzx对应新实验目录。无Test6/independent final/held4、失败配方重跑、追加seed或重复资源审计。
