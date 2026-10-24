# D26 B0部分原件复核（2026-10-02）

证据提交：[872e246](https://github.com/66322/remote_sensing_frequency/commit/872e246c99559d1777b03e329a1febee0c52a976)。最后上传queue观测2026-10-02T22:22:14.689169+08:00，RUNNING/COMPLETE1/9；B0完成，J0/CAP评价阶段，其余待执行。不是当前实时状态，完整D26结论待剩余原件。

运行research_d26_bidirectional_20261002T191253_1513109；固定执行52f94388b1a9c7557e9ef533075661139cd55eda。Potsdam Val2=3_11/5_10，seed42，训练8000、validation三状态选step4000，native512window/stride256，NoBoundary pooled fg5。B0 selected SHA=8c1b517311afa4188a01750b2d2edfd0fb84446d8062a65133fcfa3f0783ceee。原单模态checkpoint、数据/配置在原plan绑定。

|条件|B0|相同输入固定RGB|差值pp|
|---|---:|---:|---:|
|clean|87.124712|86.397930|+0.726782|
|rgb_down4|84.335502|82.318344|+2.017157|
|aux_noise_std010|86.984913|86.397930|+0.586983|
|aux_shift8 pooled|86.490642|86.397930|+0.092712|
|四族等权综合|86.085607|85.394634|+0.690973|

aux_shift8在3_11相对RGB−0.496337pp；rgb_blur5+aux_shift8在3_11−0.273260pp。因此pooled有益不等于每tile安全。DSM noise010独立专家5.124372，而融合仍正，质量与任务伤害不能等同；head自加工可能解释部分收益，需同carrier DSM中和对照。

clean full六类计数：仅DSM正确1,992,856中融合保留783,274（约39.3%）；仅RGB正确12,457,061中丢833,246；双方正确48,411,190中丢103,321；双方错误4,112,169中纠正314,778。计数含clutter且口径为full，与NoBoundary fg5 mIoU不同。净纠错数量不是mIoU差值。

已核对36个selected逐tile原件（10primary+2missing+6local，两个tile），432个full/NoBoundary availability联合计数区域；joint边缘与R/D/candidate混淆矩阵一致，selected绑定一致。派生报告见[JSON](../../records/research_d26_b0_review_20261002/recomputed_review.json)。未逐字读取超大summary、未检查247文件全部SHA、未下载权重/预测；不称全量产物审计完成。

RGB缺失=B0原DSM，DSM缺失=B0原RGB，属于结构回退，不是新缺失精度收益。J0/CAP当前仅step8000选模时三状态结果，不作完整性能排名。B0是普通融合强基线的阶段证据；尚无D26频率/语义/双向交互独立贡献结论。
