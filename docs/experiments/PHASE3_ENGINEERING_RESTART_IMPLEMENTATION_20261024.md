# 已授权的一次工程修订启动准备（2026-10-24）

用户在CPU预检通过后明确要求“继续，把实验启动”，授权本次零训练更新工程失败的一次修订尝试；原失败记录保留，不改变一般失败不自动重跑规则。

执行提交[752d3835a18a15a04d83b1dcc1841bff98bf0b07](https://github.com/66322/remote_sensing_frequency/commit/752d3835a18a15a04d83b1dcc1841bff98bf0b07)。[完整执行协议及命令](../protocols/PHASE3_ENGINEERING_RESTART_EXECUTION_20261024.md)。已实现实际M2/J/R的Python3.9兼容副本、匿名memfd、明确M2选择、首次失败止队、双方入口就绪后放行、Fit12输入身份一致性、缺catalog等待和全局重复启动拦截。原科学计划、预算和门禁不变。

本地41项通过，独立无.git包的14项重验通过，七文件Python3.9语法解析通过，[本地回执](evidence/PHASE3_ENGINEERING_RESTART_LOCAL_20261024.json)。提交中逐文件SHA已对Git原件核验。服务器真实新目录CPU检查、原16项和合并11项/首次CUDA更新仍待用户执行；当前没有新PID或新run目录回执，不宣称实验已启动。

新run在执行时生成records/research_phase3_m2_revision_<时间>_<PID>和research_phase3_combined_revision_<时间>_<PID>，全局单次回执records/phase3_engineering_restart_20261024_once.json；旧两run完整保留。所有修订快照、CPU检查和训练记录在/home/jovyan/zzx。用户操作、无SSH，只GPU0/1；test封存、无新增seed/预算/失败自动重试。
## 目标服务器登记后停止：已准备同目录接续

2026-10-24 09:30:32用户回执确认752d修订已经在09:28:14登记M2/合并两目录，新CPU模型、原M2全16项、combined_plan6项通过，但J头因model常规包遮蔽合并命名空间目录而导入失败。无launch/release/jobs，GPU0/1空闲；尚无训练更新。

之前41项为单仓库检查，没有覆盖这个分包布局，属助手打包/测试覆盖遗漏。现已在真实分包布局复现并修复，8项路径/接纳检查及原三套11项通过，详见[同目录接续协议](../protocols/PHASE3_MODEL_NAMESPACE_CONTINUATION_20261024.md)。不重新登记、不删除全局回执，不修改752d冻结代码；附加补丁独立绑定。当前服务器补丁尚未执行，旧启动命令不再使用。