# Phase3-M1归档独立验收

完整解释见docs/experiments/PHASE3_M1_ACCEPTANCE_AND_ROUTE_REVIEW_20261015.md。

- 输入固定提交：09fb57a6ec26f6367c9891f2aa924cc4bf7219cc。
- verification.json：归档和算术复算范围及明确限制。
- analysis.json、primary_table.csv：主表、配对差值、关键面板条件补救/伤害与尺度诊断；均为充分整数统计派生。
- manifest.json：原归档清单。
- download_archive.py：只读下载29块，逐块/整体/内含4168文件校验，生成evidence和archive_verification.json。不加载模型或使用GPU。
- audit_results.py：独立重算CM、联合边际、救回/损伤、主对比、门禁、样本流和恢复来源，生成audit_result.json。不调用原计数函数，不重做模型推理。

如需复算，在本目录副本运行：

```bash
python -B download_archive.py
python -B audit_results.py --source-code /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_phase3_m1_recovery_20261015T164357_19327/code
```

依赖Python、NumPy及原绑定的256份code源码；pth、原始影像、CUDA均不需要。--source-code用于核验执行源码哈希，不能指向其他版本源码。固定提交也可以从GitHub复原相应文件；不要完整克隆含大归档的仓库来做本次复核。

VERIFIED仅指归档与计数算术；模型张量、原始数据、历史旧run CM/流的跨run核验及物理GPU归属不是本次独立重跑证明。两个重复使用的Val tile、两个DSM seed和一个固定RGB seed不足以支撑独立地理泛化或可靠的seed总体置信区间。辅助校准/激活/GPU绑定记录不完整，详见报告。

本地复算结束后只清理自己生成的parts、core.jsonl.gz、evidence下载副本，保留上述脚本、manifest、验证回执和分析产物。服务器权重、输入与研究原件不属于这次清理范围。
