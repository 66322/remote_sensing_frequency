# 状态与证据接收

最后服务器观测：2026-10-04T18:24:33.785422+08:00，来自用户粘贴终端状态；QUEUE=RUNNING，控制器PID2720259，LIVE=True，主体12/18完成。A0—A5及B1—B6 COMPLETE；C0/C1 RUNNING fixed8000，step8000/8000、windows529/529，最近进度18:24:22，仍非COMPLETE；C2—C5 PENDING。F仍PENDING，B3 gate=False，实际SKIPPED_GATE尚待确认。该观测晚于18:07已上传记录快照，不能替代C完成原件，也不代表实时状态。

固定A2 gate=False：综合对A0+0.101643pp（要求≥+0.2）、对A1−0.044694pp（要求≥+0.2）、对A3−0.023958pp（要求≥+0.1）；其余原生安全/fixed检查通过。固定B3 gate=False：几何对B1+0.021260pp（要求≥+0.5）、对B4−0.012852pp（要求≥+0.2）；DSM锚点正确伤害率较A0增加0.011997pp。F触发条件不成立；不追加A/B种子、追训、扫参或换敏感性最佳组救gate。原C继续。

D23—D28保持已整理结论；D30紧凑原件已收，完整逐tile矩阵未到。Post A/B十二组技术完成，原件上传成功，关键七组整数计数复核PASS；C0/C1在fixed8000评价阶段且未COMPLETE，余C待接；F条件False但实际跳过标记未见。

efba23a56eb7f508c0485332cc03c6476bfc8d59上传1769文件，manifest创建18:08:15，原件1899293890字节、上传165121503字节。实际回读plan、portfolio_screen、queue、最新repair_manifest及A0/A1/A2/A3/B1/B3/B4七组complete、selected/fixed8000共14份summary；核对上传与原始SHA、plan/执行绑定和complete的summary SHA，离线核对54432组6×6矩阵tile→pooled及fg5重算、5292组joint汇总和candidate边际一致。A4/A5/B2/B5/B6仅读原生阶段汇总，未逐份验收全部1769文件；未读取服务器权重/预测本体。

上传体积修复服务器成功：165121503字节，低于门禁。修复manifest已收到确认2a15ef与A_optimizer_updates=0。具体口径与结论见[报告](../experiments/POST_D30_AB_RESULTS_20261004.md)。

主线仍RGB–DSM双向条件互补与退化/缺失分割，恢复是旁支，仍处于可行性探索，无确认性新贡献。用户终端操作无SSH，只用GPU0/1两张H10080GB、nohup、seed42/8000步/batch16无累积，全部记录/缓存/快照在zzx对应目录。不重复资源审计，不加seed，不读取Test6/独立final。

## 后续候选池（规划，未启动）

用户2026-10-04要求依据结果和论文多规划实验；已形成[8类后续实验候选池](../protocols/POST_AB_FOLLOWUP_PLAN_20261004.md)：2类诊断/压力评估、6类训练研究，最多26个新增配置，按条件触发，首批建议N1交互位置×适应四组。主线与原C/F门槛不变，未新建队列。该排序是助手建议，尚不是用户选定执行路线；不重训A/B、不加seed、不启动F、不访问Test6。C双侧通过才触发教师来源检验；失败不自动换教师挽救。
