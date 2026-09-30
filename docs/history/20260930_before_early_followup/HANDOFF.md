# 当前交接：确定性填充反传故障已定位，修复待服务器复测

最后带时钟的新服务器记录：2026-09-30 00:18:15+08:00，多方向队列通过 Python 3.9 DINO 实际导入检查，重新进入首个 D 组微批短测；首步反传因 `replication_pad2d_backward_cuda` 不支持严格确定性而失败。没有生成 `scope.json` 或训练检查点，后台队列已退出，**未启动正式训练**。这是用户贴出的历史输出，不代表当前实时状态。D21 原48项队列更早于2026-09-29 18:23:44+08:00按预定 STOP 退出，旧记录为 `32/48 INCOMPLETE`，有效双种子范围为 `32/32 COMPLETE`。

[D21结果报告](../experiments/D21_DETAIL_FREQUENCY_RESULTS_20260929.md)记载预设 F2 候选四块增益均未达 +0.2 pp，DSM 完全缺失的四块安全门槛也全部失败；Vaihingen 有逐 tile 负迁移。D21 开发筛选关闭，Test6 和独立 final 均未启用。原运行和归档命令见[历史交接](../history/20260929_before_d21_results/HANDOFF.md)。

用户已要求按[新计划](../protocols/POST_D21_MULTIDIRECTION_DAY_PLAN_20260929.md)执行。现有 A/B/C/D/E 模型、50项清单驱动的训练/评价与两卡队列。Python 3.9 本地兼容镜像和 DINO 实际加载已在服务器通过；恢复路径的可微补边与高频边界现改为确定性零填充，A/B 锚点计算不变。**本次修复尚未在服务器短测，正式训练也尚未启动**。主计划42项，备用8项，全部seed42。

吞吐旧短测[原始 JSON 与 GPU 采样](../experiments/POST_D21_THROUGHPUT_PROBE_RESULTS_20260929.md)归档于 `6e45fce`，不能用于新模型 ETA。下一步服务器拉取本分支，依次运行 `--prepare-only`、`--profile-only`；核对新 `scope.json` 的预计工时/资源后，`--launch` 自动完成冻结范围。缺失资产先说明，不自动下载。D9B固定边缘分数的负结果使旧D22固定Sobel门不再是主方案；B缺失回退只作为工程不变量。上版交接见[历史](../history/20260929_before_multidirection_plan/HANDOFF.md)。
