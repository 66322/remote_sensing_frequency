# 下一实验：Phase 1.5 双卡零训练诊断

状态：**PHASE_1_5_V1_1_PLANNED_AWAITING_IMPLEMENTATION_AND_SMOKE**。用户授权GPU0/1、一天以上且未完继续；当前暂不处理单卡释放。新队列未登记，不能运行旧enqueue来冒充本轮。

[双卡具体规划](../protocols/PHASE_1_5_TWO_GPU_PLAN_20261012.md)、[Phase1.5主协议v1.1](../protocols/PHASE_1_5_RECOVERABILITY_20261012.md)、[文献映射](../literature/PHASE_1_5_METHOD_CANDIDATES_20261012.md)、[关键原件复核](../experiments/LATEST_RESULTS_KEY_REVIEW_20261012.md)。


## 固定清单
E：旧S1 block-like三族120case空间profile，优先CPU。
A：S1/R16×四DSM干预×四mask族×20×2tile，1280逻辑missing case，匹配DSM条件clean参考。
B：S1 pixel 5/10/25% nested，新增80；PE(r)=NA。
C：五类/Car−Building及新错恢复计数，复用全部推理。
D：同输入五expert pool，raw组合、pixel/128/256 oracle、部署观测分箱；新增S1-3 160、DSM-only2，其余复用。旧label无熵时S1160case只补熵并校验label exact。

核心新增1378，含最多160熵补全约1538；两卡24–48h预留，不设24h截止。先按实测秒/case修正ETA，不按时长扩大实验。

## 立即工程工作
复用Structured native链与cache，独立快照/manifest/任务清单；smoke用真实编号1/tile3_11，修复512网格边缘双射。执行主协议known-answer及跨GPU一致性、clean匹配、oracle分母、熵与label replay检查；全PASS后才登记全量，技术失败HOLD保留证据。服务器由用户执行、无SSH，记录/临时数组均/home/jovyan/zzx。

## 后继不自动启动
五项完成并轻量原件核验后再评审残差context或固定专家router；灰区可评审matched DSM-only但不即刻训练。两tile/单seed开发边界保持，不扩Phase1A、不加seed、不Test6/held4/final。不把已规划四组训练草案算本轮队列。
