# M2结果证据索引

本目录用于两台电脑从GitHub直接接续。来源为用户2026-10-29回传的服务器终端；不冒称助手直连服务器或完整矩阵已独立重算。

| 文件 | 内容 |
|---|---|
| summary_from_terminal.json | 108训练/77,868评价完成态及总判定 |
| gates_from_terminal.json | 全部已回传G0—G4/H2条件及精确差值 |
| REPORT_from_terminal.md | 服务器08:43原报告，21行RGB-down4主表 |
| down4_main_results_from_terminal.csv | 相同21行主结果，可直接读表 |
| clean_dsm_results_from_terminal.csv | 3fold×3seed×7臂=63行正常输入DSM结果 |
| gate_checks_from_terminal.csv | 120个已回传判定差值项，不是120个独立实验 |
| experiment_conclusions.json | 机器可读结论、支持范围及未回答问题 |
| artifact_availability.json | GitHub已有与服务器保留原件清单 |
| server_terminal_20261029T102937.txt | 用户原始终端，含J错误原栈及完整回传 |
| derived_analysis.json | 主报告配对差值摘要，保留原记录 |
| PROVENANCE.json | 来源及原件接收边界 |

REPORT_from_terminal.md是08:43的原始报告，其中“全部模型保留服务器”描述的是当时状态，原文不事后改写。11:05用户授权清理后实际仅保留18个R/D0，见[清理回执](../phase3_m2_cleanup_20261029/)。所有科学表和判定仍保留。

完整服务器metrics.csv、三fold压缩充分计数、全alpha/margin/校准、manifest和证据索引未直接接收；科学结论来自回传主表与gate差值。原件仍服务器保留，可复用二次分析，无需重新训练。详见[完整实验记录](../../docs/experiments/PHASE3_M2_ACCEPTANCE_AND_CLOSEOUT_20261029.md)。

中央入口：[实验索引](../../docs/experiments/rebuild_v1/INDEX.md)、[注册表](../rebuild_v1_experiment_registry.json)。
