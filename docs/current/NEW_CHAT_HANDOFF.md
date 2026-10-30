# 新对话稳定接续入口

本页仅为长期跳转，不记录运行PID、进度或待执行的历史启动命令。服务器状态以带时间戳原件及当前文件为准。

1. 从GitHub权威分支读取[共享入口](../START_HERE.md)，再读[研究决定](RESEARCH_DECISION.md)、[当前交接](HANDOFF.md)、[状态](PROJECT_STATUS.md)、[下一步](NEXT_EXPERIMENT.md)。
2. 遵守[仓库长期规则](../../AGENTS.md)、[跨对话执行约定](../protocols/EXECUTION_CONTRACT.md)和[共享记录规则](../protocols/RECORD_SOURCE_AND_HANDOFF.md)；启动链开发/打包/修复须按[启动交付与故障控制](../protocols/STARTUP_DELIVERY_AND_FAILURE_CONTROL.md)执行。
3. 新计划立项/排队及计算配置改动前，必读[实验规划规范](../protocols/EXPERIMENT_PLANNING_RULES.md)并填写[准备表](../templates/EXPERIMENT_PREFLIGHT_TEMPLATE.md)：探索默认单种子，必要重复通常先两个，三及以上说明具体必要性和成本；真实训练/评价吞吐须有证据，低利用率问题须追踪。只读接续已有运行不因此重跑预检或训练。
4. 先明确实验问题、角色、最后观测、科学源/运行修订与已验证绑定、当前唯一下一步。已有运行先只读接续；新对话不触发重新预检、下载启动包、修复、重启、清理或新增训练。
5. 需要新执行版本时按实际下载包、分目录快照和真实目标模型/环境检查；复用未变的已通过证据。共性工程故障首败停止派发，不让同一错误扩为整批失败。已有明确授权不反复询问。
6. 工程实现、本地/目标检查、正式优化更新、完整验收和GitHub同步分别报告。研究角色及科学门禁不从任务顺序、单个正结果或工程故障推断改变。

[2026-10-24启动复盘](../experiments/PHASE3_STARTUP_POSTMORTEM_20261024.md)为规则来源与具体教训，不是要再次执行的修复计划。日期命名接续页仅保留历史链接，不能以其旧运行描述覆盖当前状态。
