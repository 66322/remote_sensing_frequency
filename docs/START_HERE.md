# START HERE：D25八组具体执行

共享权威分支rebuild-v1-protocol-20260915；2026-10-02用户明确授权D25具体实验，固定代码0c31167d0fdb57f03459ea18981c1ee02bcee9f2已实现、12本地CPU行为检查PASS，服务器启动观测待回传。

读取顺序：
1. [研究定位与决定](current/RESEARCH_DECISION.md)
2. [当前交接](current/HANDOFF.md)
3. [当前状态](current/PROJECT_STATUS.md)
4. [下一步](current/NEXT_EXPERIMENT.md)
5. [D25固定版本nohup执行](protocols/D25_EXECUTION_20261002.md)、[科学协议](protocols/D25_MISSINGNESS_OPTIMIZATION_PLAN_20261002.md)

GPU0/1两H10080GB、RAM/磁盘充足、batch16无累积，全部产物在zzx对应实验目录。一次启动固定八组，不重复资源/预算审计；收到实际目录/PID/step再记录运行状态。

[D24复核](experiments/D24_REVIEW_AND_PAIR_CORRECTION_20261002.md)：15/15技术完成且原件已上传；A1/A3 Pair未启用，消融无效，不可称Pair失败。D25 P1正确信号重新与P0比较。[近期文献映射](literature/D25_OPTIMIZATION_AND_MISSINGNESS_20261002.md)用于假设来源，已有技术不自动成为贡献。

主问题未变，C1恢复旁支，最终贡献未冻结。Test6禁读，重复Val2及历史held4暴露不独立final。
