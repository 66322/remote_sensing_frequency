# 当前交接：D24十五组完成，上传完整轻量证据

更新2026-10-02 12:10:21（Asia/Shanghai）。共享分支rebuild-v1-protocol-20260915；执行固定版本cf1955d966163978b5c8af433f3845b5ca05da9e。[上次交接归档](../history/HANDOFF_20261002_BEFORE_D24_COMPLETION_OBSERVATION.md)。

最后观测：用户回传队列记录2026-10-02T04:06:59.332637+08:00，COMPLETE 15/15；所有组4000/4000，最后B3完成标记04:06:53.704712，汇总summary_exit=0、test6_loaded=False。见[完成观测](../../records/research_d24_completion_observation_20261002/observation.json)。已收到15组四位小数指标；完整screen_result、逐tile/条件原计数、选模绑定与梯度检查尚未上传/复核。查询显示的12:09 ROUGH_QUEUE_END是查询时间加零剩余，不是实际完成时间。

阶段为可行性探索；问题仍是光学可用时DSM有益融合、负迁移与缺失。D23当前TSF解法关闭，C1恢复旁支、部分解冻强基线；当前没有方向变更或最终贡献采纳。D24为看结果前冻结的A表示/Pair、B同容量类别原型/平衡、C光学KD、D退化/缺失增强四角度15组，seed42/fit12/Val2、每组4000步、物理batch16无累积、BF16训练、FP32评价。Test6禁读；本次单seed重复开发Val2不等于独立确认。

用户stdout初步信号：A2相对A0综合约+2.9868pp；Pair近零，类别原型相对同容量近零，类别平衡组综合下降约3.45pp；C2低于C0；D1相对D0约+0.5791pp，且是打印综合最高组86.4448。这些只来自同轮四位小数输出；D1是普通增强对照，不能自动升级为机制贡献或新主线。必须复核精度保护、逐tile、未见条件、harm/rescue、缺失和完整冻结判定；不按综合名次追加训练或放宽门槛。

立即由用户服务器终端上传本次已有目录；不再恢复/重启D24，不跑资源审计。GPU0/1均H10080GB、RAM/磁盘充足、nohup和zzx目录规则已确认。所有原件仍保留对应目录，预测/checkpoint仅索引、不上普通Git。主副本不checkout/reset。

```bash
cd /home/jovyan/zzx/paper_rebuild/08_thesis_full_repro
D24_DIR="$PWD/records/research_d24_overnight_20261002T000843_877409"
python -B "$D24_DIR/code/scripts/upload_rebuild_v1_d24_records.py" --root "$PWD" --directory "$D24_DIR"
```

上传后贴D24_GITHUB_COMMIT与D24_GITHUB_RECORDS；下一对话先读最新GitHub入口，再按manifest读取完整记录、复核配对对照/冻结判定。服务器由用户执行，无直连。协议最多两条通过假设另立确认；当前未授权额外自动训练、多seed或扫描。
