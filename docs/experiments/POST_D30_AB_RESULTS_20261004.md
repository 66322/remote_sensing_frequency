# Post-D30 A/B原件与固定候选分析

固定A2 gate=False：综合对A0+0.101643pp（要求≥+0.2）、对A1−0.044694pp（要求≥+0.2）、对A3−0.023958pp（要求≥+0.1）；其余原生安全/fixed检查通过。固定B3 gate=False：几何对B1+0.021260pp（要求≥+0.5）、对B4−0.012852pp（要求≥+0.2）；DSM锚点正确伤害率较A0增加0.011997pp。F触发条件不成立；不追加A/B种子、追训、扫参或换敏感性最佳组救gate。原C继续。

结论等级：实验已验证，限单seed42与重复开发Potsdam Val2=3_11/5_10阶段证据；不是独立确认或正式test。

## 配置与验收范围

运行ID research_post_d30_mechanisms_20261004T000812_2446364；科学执行01ec8dee82f7e272f6a650aaf9f3e619a0e7c516；恢复2a15ef163c3df7e96ee52c81cb677ebdb1305935。[plan](https://github.com/66322/remote_sensing_frequency/tree/efba23a56eb7f508c0485332cc03c6476bfc8d59/records/research_post_d30_mechanisms_20261004T000812_2446364/evidence_20261004T180809837028_3002648/plan.json)：seed42、8000步、物理batch16无累积、native512/stride256，三种完整/单侧clean均值选模，同分选早。指标NoBoundary mIoU_fg5；S_available为C/QR/QD/QJ四族均值等权平均；几何为四预设合成故障平均、8px内边界支持，不是自然配准误差证据。原生汇总A/B十二组selected均8000，独立绑定核验限七关键组。新流不能与D26/D30旧分数严格匹配因果排名。

efba23a56eb7f508c0485332cc03c6476bfc8d59上传1769文件，manifest创建18:08:15，原件1899293890字节、上传165121503字节。实际回读plan、portfolio_screen、queue、最新repair_manifest及A0/A1/A2/A3/B1/B3/B4七组complete、selected/fixed8000共14份summary；核对上传与原始SHA、plan/执行绑定和complete的summary SHA，离线核对54432组6×6矩阵tile→pooled及fg5重算、5292组joint汇总和candidate边际一致。A4/A5/B2/B5/B6仅读原生阶段汇总，未逐份验收全部1769文件；未读取服务器权重/预测本体。

原件：[目录](https://github.com/66322/remote_sensing_frequency/tree/efba23a56eb7f508c0485332cc03c6476bfc8d59/records/research_post_d30_mechanisms_20261004T000812_2446364/evidence_20261004T180809837028_3002648)、[screen](https://github.com/66322/remote_sensing_frequency/tree/efba23a56eb7f508c0485332cc03c6476bfc8d59/records/research_post_d30_mechanisms_20261004T000812_2446364/evidence_20261004T180809837028_3002648/portfolio_screen.json)、[manifest](https://github.com/66322/remote_sensing_frequency/tree/efba23a56eb7f508c0485332cc03c6476bfc8d59/records/research_post_d30_mechanisms_20261004T000812_2446364/evidence_20261004T180809837028_3002648/upload_manifest.json)。[独立复核JSON](../../records/post_d30_ab_offline_audit_20261004/audit_result.json)；无损记录解码后核对source SHA，不以Git blob SHA代替原文件SHA。修复manifest确认2a15ef、原plan/code签名不改、A_optimizer_updates=0；未对服务器模型权重重新算SHA。

## A：共享对齐没有达到增量

| 组 | selected综合(%) | 对A0(pp) |
|---|---:|---:|
| A0 无对齐 | 85.791260 | 0 |
| A1 全128维 | 85.937598 | +0.146338 |
| A2 共享64维固定候选 | 85.892903 | +0.101643 |
| A3 错配共享 | 85.916861 | +0.125601 |
| A4 权重0.03敏感性 | 85.872685 | +0.081425 |
| A5 权重0.3敏感性 | 85.895156 | +0.103896 |

A2的clean/最差tile/双侧独有集合保留/双侧伤害/fixed同号原生检查通过，但三个机制增量条件失败。A3不低于A2，本轮不能证明正确空间对齐的特异收益；不等于整个对齐问题失败。A1略高也不用于事后改换固定候选或加预算。

## B：局部对应未超过普通增强与错配

| 比较 | 几何差(pp) | 预设要求(pp) |
|---|---:|---:|
| B3−B1普通增强 | +0.021260 | ≥+0.5 |
| B3−B4错配 | −0.012852 | ≥+0.2 |
| B3−B1 tile 3_11 | +0.011272 | >0 |
| B3−B1 tile 5_10 | +0.027743 | >0 |

B3综合85.810897%，对A0+0.019637pp，clean对A0−0.010842pp，原生综合/clean下限通过。DSM锚点正确伤害从A0的3.726151%升到B3的3.738148%，增加0.011997pp，严格不增条件失败。其余保留/安全、各tile正增量及fixed同号原生检查通过。这些小正值没有满足冻结增量，不建立对应收益。B5/B6仅搜索范围敏感性，不替代B3。

F触发gate已False；原控制器到条件阶段应按协议跳过，但当前仍PENDING，不倒写已SKIPPED_GATE。保留解释性结论、关闭A/B这两个复杂机制的当前配方，不重训、不加seed挽救。

## 后续

最后服务器记录快照：2026-10-04T18:07:21.987874+08:00，queue_status=RUNNING，主体12/18完成，A0—A5及B1—B6 COMPLETE；C0/C1在GPU0/1训练至8000步，phase=checkpoint_selection，尚非COMPLETE；C2—C5 PENDING，F仍PENDING。该快照未新查PID存活；最近存活证据为17:21用户查询。不把18:08上传时间当运行完成时间。

继续原C，固定C2在两种剩余模态分别对C0/C1/C3及自身锚点下限判断，C训练8000步不等于评价完成。待C稳定完成及F实际跳过记录后上传最终快照。不因A/B失败否定整个双模态问题；C若被普通监督追平则按原去留条件关闭该机制。

主线仍RGB–DSM双向条件互补与退化/缺失分割，恢复是旁支，仍处于可行性探索，无确认性新贡献。用户终端操作无SSH，只用GPU0/1两张H10080GB、nohup、seed42/8000步/batch16无累积，全部记录/缓存/快照在zzx对应目录。不重复资源审计，不加seed，不读取Test6/独立final。
