# 当前交接：合并队列待启动，新增期刊方向建议待选择（2026-10-22）

共享事实来源为 GitHub 66322/remote_sensing_frequency 的 rebuild-v1-protocol-20260915 分支。研究仍处可行性/机制筛选；RGB–DSM 条件互补及退化/缺失分割为当前主线，恢复旁支。M1幅度机制已按门禁关闭，M2没有运行结果。

用户最新要求参考近期遥感期刊，主动探索RGB–DSM之外的方向。本轮完成[代表性文献扫描和候选实验](../experiments/REMOTE_SENSING_JOURNAL_OPTIONS_20261022.md)，助手建议优先考虑旧地图更新、地理标注选择、异步SAR–光学事件水域制图。它们改变任务/监督/部署条件，尚未成为用户选择的新主线或新增训练合同。此建议较此前几何路线优先更开放，来源是用户最新选题诉求，不是未运行M2的负结果。已排T/V不可重复算新增。

当前执行状态不变：M2→J→R→T→V代码已实现，最多228作业/5,088,000更新，尚未登记或启动；未查询到服务器当前GPU状态，未下载新数据。执行代码提交仍是[90b9bbe](https://github.com/66322/remote_sensing_frequency/commit/90b9bbe8f4fe4777aa10b11aea48ddd572785a39)，本次仅文档更新。M2冻结提交ac325cdbb403ebb95b5eb0acbf17fffa5441dcfd，原108×32k及科学门禁不变；B90/C81仍未开放。

[合并队列执行合同](../protocols/PHASE3_COMBINED_QUEUE_EXECUTION_20261022.md)保留原启动/inspect流程。服务器由用户终端执行，无SSH；只用物理GPU0/1。M2 G0完整通过才开始J，后段依赖完整性而非挑选正结果。T/V需要独立公开开发数据和有效catalog，缺数据为WAIT_PUBLIC_DATA；失败停止，无自动重试或加种子。CPU单元测试只证明接口/小样本数据流，未完成真实数据和Linux CUDA运行验证。

新建议的下一不确定性：旧图是否提供可用增量且不会抹掉真实变化；地理覆盖是否已解释低标注收益；异步数据是否有可靠时间真值和足够事件差异。候选先核验数据与强基线，后选一条进入长程研究，不自动把A/B/C全加入现有队列。DynamicEarthNet补全产品不能直接证明真实在线性，EVLab标签仅新增开发地，水域标签不能自动等同洪水新增淹没；详见候选报告。

旧Val2/Test6/held4/final及新数据公开test继续封存。未来运行原件与执行快照全部保存于/home/jovyan/zzx独立目录，中间数据有界内存处理。结束后先核验轻量原件、统计与轨迹，再形成结论并同步GitHub回读。[上一交接已归档](../history/HANDOFF_20261022_BEFORE_JOURNAL_OPTIONS.md)。
