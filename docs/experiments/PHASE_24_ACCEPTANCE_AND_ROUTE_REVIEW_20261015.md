# Phase2.4 完整原件验收与研究路线评估（2026-10-15）

## Material Passport

- Origin Skill: academic-research-suite / experiment-agent；validate。
- Verification Status: ANALYZED。已独立核验归档与整数统计，未重跑GPU训练/推理，不标为完整实验复现 VERIFIED。
- Version Label: phase24_acceptance_v1。
- 证据固定提交：76ae973b869eb3c377be4dae99fcb7224c9e2ac3；执行快照：5a84f0eacabe5d6f1c7ed1638e6a9291c58e151f。
- 范围：Potsdam Fit12 / 反复开发 Val2（3_11、5_10），seed42，NoBoundary mIoU_fg5。差值均为百分点pp。

## 1. 验收结论

原件传输、来源绑定和整数计数复算通过；预注册 calibrated 与 probe 联合门禁均未通过。T0完成8000更新；T1/T2/T3按门禁未派发。原Phase2的L=False、B1/B3未派发不变。本次没有启动新实验、追加seed、访问Test6/held4/final或修改旧门槛。

本轮保留两条开发发现：T0-clean相对旧B0-mixed有较大改善；探针存在跨tile的RGB故障补救收益，但保护仍不足。完整对照还表明，简单RGB零值规则可解释很强的局部缺失收益。建议收束本轮候选，停止默认追加同信息、同输出动作的融合头；下一步先做问题论证和数据可达性检查。A/B相邻方向尚未选定、尚未授权新训练。

## 2. 原件与执行链

| 核验项 | 实际结果 |
|---|---|
| 分块 | 3249个，逐块SHA通过 |
| 重组归档SHA | `c2ed75c3f88601db3c8b8f644749eedf5762bdb3717f12ea09f77221b939a108` |
| manifest SHA | `9c91050676d37825e8efd654c6ee2d3c030a01b718b690d44fa549ca68c04b06` |
| 原文件 | 3014个，逐文件SHA/字节数通过；总原字节1883553558 |
| 原计数记录 | 2972条；分阶段{"SMOKE": 12, "D1": 632, "D2": 642, "D3": 522, "E": 1164} |
| 整数CM | 249248组，非负整数/ROI分割核验 |
| 联合计数边际 | 605088项，精确对应R/D/候选CM |
| correctness flow | 201696组，联合计数重建一致；空间block总计一致 |
| 来源锁 | 2328条，源/目标不同、源参数SHA匹配 |
| 跨阶段原系统CM | 46560项，D2/D3与E逐字段相同 |
| 源码/配置 | 242个哈希全部对应到公开提交；其中9个继承历史版本已单列来源 |
| 汇总、主门禁、配对mask区间 | 独立实现复算，派生浮点差异小于1e-10 pp |
| T0训练原件 | 8000条基础流记录、401条轨迹；SHA及步序通过 |

原始输入、mask和服务器.pth没有下载到本机重新hash；48个输入数组、240个mask及4个原权重的绑定依据上传原件及已验证代码执行链。输入角色仅Fit12/Val2，未新增测试数据。旧B0的完整原batch流本轮未再次下载逐行比较；T0运行回执stream_verified及源码逐步硬检查与原Phase2已归档的初态证据一致。这些边界不影响当前整数计数复算，但不能宣称重新独立训练复现。

SMOKE12与D1新632合计644条，其中10个核心smoke复用于D1，使D1累计为642；不要把2972条记录与重复stage标签机械相加成重复实验。

## 3. 预注册主门禁：原结论保持

| 检查项 | 要求 | calibrated | probe |
|---|---:|---:|---:|
| 全P-U对reference | ≥+0.3 | -0.020604 | +1.744472 |
| RGB-fault对reference | ≥+0.5 | -0.056578 | +3.480202 |
| RGB-fault，3_11 | >0 | -0.114156 | +6.503460 |
| RGB-fault，5_10 | >0 | -0.003354 | +0.723619 |
| 最差family×damage | ≥-0.5 | -0.467897 | -0.358382 |
| availability回退 | exact | true | true |
| 联合接受 | 全部通过 | false | false |

探针失败项：clean/3_11相对reference -0.223892，clean/5_10 -0.342111，P-U healthy/5_10 -0.296920，均低于-0.2门槛。其余已登记保护项通过，包括相对RGB-only的保护。

因此可以说当前探针具有固定两tile下的补救正线索，但没有同时保持强静态参考的clean/healthy优势。不得改为只对RGB比较后倒写通过，也不能把这个失败概括成没有可部署信息。

## 4. T0：匹配的头训练分布对照

T0与旧B0同结构、同初态、同基础crop/GT token流、同优化器与8k预算，专家冻结；处理差异为clean与mixed。T0是8参数静态头：2个全局温度、6个输出类别的静态RGB/DSM混合系数，不使用15个质量信号做动态决策。参数JSON中的feature_names不是它实际使用质量信号的证明。

| 面板 | T0 8k | T0−B0-mixed | T0−source静态reference | T0 8k−4k |
|---|---:|---:|---:|---:|
| clean | 86.9892 | 2.6180 | 0.1086 | 0.0606 |
| P-U | 78.2555 | 2.4989 | 0.3163 | 0.0559 |
| P-M | 77.3547 | 1.5479 | 0.1950 | 0.0405 |
| dose | 74.8222 | 3.3476 | 0.2943 | 0.0765 |
| ordinary | 80.0920 | 2.8318 | -0.0261 | 0.1152 |

T0对RGB-only的clean增益+0.354961、P-U增益+0.751856；对旧B0的大幅差异不能全部作为新增方法贡献。静态reference在两个fold均为source选出的alpha=0.9未校准混合。T0训练使用Fit12，D2探针使用源Val2的guarded样本，训练来源与部署实现并非完全匹配；不得把T0与探针分数差直接解释为某种信号的因果作用。

**池化均值掩盖了方向回归。** T0的RGB-fault相对reference为+1.042724，但DSM-fault在3_11/5_10分别为-0.421494/-0.390739，相对RGB-only为-0.494720/-0.403108；最差family×damage达-1.843277。因此T0也未解决联合保护。这个附加检查不改变原派发门禁，但纠正了仅凭T0池化均值判断“已安全”的风险。

4k→8k的P-U仅+0.055934，dose healthy反而-0.182566。主端点固定8k，不挑4k、不因loss下降自动延长训练。20个配对mask的T0−reference均值+0.316270，95%重采样区间[+0.311924,+0.320733]，仅条件于这两张开发tile。

## 5. 预登记敏感性对照：RGB零值规则

两fold的深度1树均选中rgb_zero_fraction（特征12），阈值分别为0.20/0.24；它没有选中DSM mean/std/gradient。

| source→target | T_RGB / T_DSM | 静态alpha | logistic采用阈值 | stump规则 |
|---|---:|---:|---:|---|
| 3_11→5_10 | 2.4667 / 2.4765 | 0.9 | 0.7 | rgb_zero_fraction ≥ 0.2000 |
| 5_10→3_11 | 1.7045 / 1.9893 | 0.9 | 0.5 | rgb_zero_fraction ≥ 0.2400 |

树的主P-U为81.742472，高于probe的79.683682；树对RGB-fault/zero相对RGB-only差值+16.955395，对RGB-fault/down4差值+0.000000。必须按损坏类型解释，不能把零值可观测收益当成一般几何质量判断或所有未知退化的解决方案。零值比例是合法的输入线索，这不是GT泄漏；它也不等于真实摄影测量匹配质量。

stump同样未通过附加保护检查：除5_10的clean/healthy相对reference退化外，最差family×damage为-0.827054。probe在RGB-fault/down4相对reference池化为-0.329724，5_10为-0.673377；“RGB-fault两tile平均都为正”不等于各损坏类型都跨tile改善。

| P-U方向 | 损坏 | RGB | source静态reference | probe | stump | T0 |
|---|---|---:|---:|---:|---:|---:|
| rgb | zero | 54.7637 | 55.9837 | 63.2738 | 71.7191 | 57.4806 |
| rgb | down4 | 81.9823 | 82.5956 | 82.2659 | 81.9823 | 83.1842 |
| dsm | zero | 86.6343 | 86.3356 | 86.6141 | 86.6343 | 85.4494 |
| dsm | down4 | 86.6343 | 86.8419 | 86.5809 | 86.6343 | 86.9078 |

| target tile | 方向 | RGB | reference | probe | stump | T0 |
|---|---|---:|---:|---:|---:|---:|
| 3_11 | rgb | 68.5358 | 69.4141 | 75.9175 | 76.8914 | 70.4617 |
| 3_11 | dsm | 87.0489 | 86.9756 | 86.9870 | 87.0489 | 86.5541 |
| 5_10 | rgb | 67.9221 | 68.8818 | 69.6055 | 76.5015 | 69.9294 |
| 5_10 | dsm | 85.9296 | 85.9172 | 85.9297 | 85.9296 | 85.5265 |

## 6. 附加门禁复算的性质与边界

下表把同一数值规则应用于T0/4k/stump，仅为**本次验收的诊断分析**。它们不是原主入场候选，不能事后取代calibrated/probe、改写已执行的派发或宣布预注册主方法成功。

| 系统 | 诊断接受 | P-U差值 | RGB-fault差值 | 未满足项 |
|---|---|---:|---:|---|
| T0 | False | 0.3163 | 1.0427 | P-U/dsm/all/3_11/reference；P-U/dsm/all/3_11/rgb；P-U/dsm/all/5_10/reference；P-U/dsm/all/5_10/rgb；最差family×damage |
| T0_4000 | False | 0.2603 | 1.2639 | P-U增益不足；P-U/dsm/all/3_11/reference；P-U/dsm/all/3_11/rgb；P-U/dsm/all/5_10/reference；P-U/dsm/all/5_10/rgb；最差family×damage |
| stump | False | 3.8033 | 7.5610 | clean/both/all/5_10/reference；P-U/both/healthy/5_10/reference；最差family×damage |

P-U的healthy/方向保护与family×damage检查不要扩写成1164面板所有ordinary/dose情形均受保护。原协议的完整报告包括这些面板，但主门禁的具体实现仍按登记函数解释。

## 7. 救回与损伤流

以下为GT类别0–4的原整数计数，按同tile/方向/损坏聚合所有固定family与realization。像素和mask重复相关，不能作为独立样本计算场景级显著性。救回指RGB错、系统对；损伤指RGB对、系统错；其净值不是mIoU差值。

| 系统 | tile | RGB损坏 | 救回 | 损伤 | RGB正确像素受损率 |
|---|---|---|---:|---:|---:|
| probe | 3_11 | zero | 273767431 | 37435627 | 2.0096% |
| probe | 3_11 | down4 | 17296177 | 4933008 | 0.2102% |
| probe | 5_10 | zero | 70263464 | 3892903 | 0.2155% |
| probe | 5_10 | down4 | 51428 | 231 | 0.0000% |
| stump | 3_11 | zero | 360874607 | 100684791 | 5.4050% |
| stump | 3_11 | down4 | 0 | 0 | 0.0000% |
| stump | 5_10 | zero | 409516977 | 85388110 | 4.7263% |
| stump | 5_10 | down4 | 0 | 0 | 0.0000% |

逐类/区域原计数与完整流见归档；本地复算文件另存correctness_flows.json。P-M/dose的合法availability回退贡献单列，不将与RGB相比的大幅缺失区差值全部归因于新头恢复能力。

## 8. 概率校准与oracle解释

目标clean的全量统计如下，NLL/Brier使用GT类别0–4；ECE为固定15等宽bins，不能单凭ECE判断优劣。正温度不改变单专家argmax，概率损失改善不保证融合分割改善。

| target | 专家 | NLL | Brier | ECE15 |
|---|---|---:|---:|---:|
| 3_11 | rgb | 0.1967 | 0.0949 | 0.0250 |
| 3_11 | dsm | 0.7791 | 0.3882 | 0.1247 |
| 3_11 | rgb_calibrated | 0.1760 | 0.0924 | 0.0107 |
| 3_11 | dsm_calibrated | 0.6454 | 0.3586 | 0.0205 |
| 5_10 | rgb | 0.2812 | 0.1271 | 0.0394 |
| 5_10 | dsm | 0.7581 | 0.3817 | 0.1226 |
| 5_10 | rgb_calibrated | 0.2681 | 0.1282 | 0.0627 |
| 5_10 | dsm_calibrated | 0.6600 | 0.3558 | 0.0551 |

校准指标也存在迁移取舍：5_10的RGB NLL从0.281239降至0.268116，但Brier从0.127131升至0.128192，ECE15从0.039404升至0.062715。不能把源拟合损失降低或某一个目标指标改善等同于整体校准、融合安全都改善。

从当前原联合计数独立重建的D0差值与旧报告一致：RGB-fault oracle−bestFixed=18.444090，B2−bestFixed=+4.248143；DSM-fault分别为3.665263与-7.609203。oracle−B2包含既有融合回归，不能全部命名为未利用互补。

归档的1000次固定预测边际跨像素参照，oracle−bestFixed均值为21.297542/6.528040，均高于实际18.444090/3.665263。该参照破坏空间依赖，不是随机oracle膨胀比例校正，也不是关闭所有router的门禁。本次核验其归档字节和实际D0差值，未独立重跑1000次随机参照。

## 9. 统计与推断检查（11/11项适用性审阅）

| 检查 | 处理与限制 |
|---|---|
| Simpson聚合反转 | 分tile、方向、zero/down4报告；不只看总体P-U。 |
| 生态谬误 | pooled mIoU不推出每像素、类别、区域改善；correctness净值不等于IoU。 |
| Berkson选择偏差 | guarded source样本仅代表相应内部区域；加权不把它变成全tile无偏样本。 |
| Collider bias | disagreement/preference子集与部署总体分开；保留bothWrong负类。 |
| 基率忽略 | 审阅救回、损伤与RGB正确基数；不把排名指标当部署收益。 |
| 回归均值 | 已知低分B0有匹配对照，但仅一次seed的处理比较，不是独立重复。 |
| 幸存者偏差 | 保留calibrated/probe失败、全部13系统、未派发头和不利条件。 |
| 多重寻找 | Val2已反复开发；无场景级p值，mask区间不替代独立场地。 |
| 分析分叉 | 原主门禁和8k端点不变；T0/stump附加比较明确标为诊断。 |
| 相关与因果 | 本次匹配处理支持限定的训练分布比较；DSM表征失配与真实质量机制仍是假设。 |
| 反向因果 | 置信度与错误可共因于场景/类别；不把输出统计直接解释为物理原因。 |

## 10. 按原对话路线作出的建议

1. **收束本轮候选，停止默认换融合头。** 当前探针在强静态保护上失败，简单静态头/零值规则又很有竞争力；继续的依据应是新的可区分假设，而非oracle空间仍大或某个新模块尚未试过。
2. **保留RGB–DSM积累，把下一交付改为问题论证。** 已有可写的匹配诊断、训练分布效应、故障可观测线索和收益—损伤边界。新算法贡献仍需强简单基线、跨场景证据和明确的新认识。
3. **优先核查A的数据可达性。** 当前包未证明能取得匹配置信度、点密度、重投影残差或配准不确定性。只有这些真实质量观测提供超出RGB零值、预测熵和分歧的跨场景任务信息，才有理由进入新机制设计。不能把人工fault mask换名为物理质量。
4. **B保留为备选机制问题。** 区分高度单位/归一化、采样密度、视野与通用适配，先看普通处理能否解释现象；不把换DSM编码器或加adapter本身当作新问题。当前DSM低分不能当信息上限。
5. **A/B均未选定或启动。** 下一步先列真实失败、可用观测、最近邻工作、最小可证伪检验和停止条件，再选择一个。继续遵守用户“优先研究问题和创新性、暂不受期限限制”的偏好。

上述为研究建议。原研究主线RGB–DSM条件互补与退化/缺失分割、恢复旁支定位没有被自动改写。没有任何新专家、seed或封闭测试授权。

## 11. 产物与工程收尾

RAM退休回执记录临时像素数组落盘为0、GPU worker均退出；T0的rolling resume与4k临时.pth已按登记规则退役，4k计数/轨迹/参数导出保留，8k端点仍有索引。未在本次验收中删除服务器数据、原专家或必要端点。

归档压缩为812.094 MiB，原文件约1.754 GiB，主要是联合计数/空间摘要；这不是几MB的小包。白名单排除.pth与像素数组，但仍包含小头参数JSON导出（jobs/T0/endpoint_weights.json, jobs/T0/trajectory_04000_weights.json）；manifest的“weights server-only”应按.pth理解，不能据此说没有任何参数公开。后续改进归档可减少冗余与输出阻塞，但本轮原件保持不变。

上传最终成功于提交76ae973b。此前本地commit阶段未及时退出，恢复后push因无HTTPS认证退出128；用户在交互会话完成认证后，原入口推送并回读成功。旧终端输出阻塞为过程解释，未因/proc权限限制获得完整系统调用证明，不把它写成已确认唯一根因。

## 可追溯入口

- [固定原件manifest](https://github.com/66322/remote_sensing_frequency/blob/76ae973b869eb3c377be4dae99fcb7224c9e2ac3/records/research_phase24_protected_20261014T193915_2149100/light_evidence/manifest.json)
- [固定原摘要](https://github.com/66322/remote_sensing_frequency/blob/76ae973b869eb3c377be4dae99fcb7224c9e2ac3/records/research_phase24_protected_20261014T193915_2149100/light_evidence/summary.json)
- [执行协议](https://github.com/66322/remote_sensing_frequency/blob/5a84f0eacabe5d6f1c7ed1638e6a9291c58e151f/docs/protocols/PHASE_24_EXECUTION_20261014.md)
- [科学门禁](https://github.com/66322/remote_sensing_frequency/blob/5a84f0eacabe5d6f1c7ed1638e6a9291c58e151f/docs/protocols/PHASE_24_DIAGNOSIS_AND_CONDITIONAL_HEADS_20261014.md)
- [原路线复盘](https://github.com/66322/remote_sensing_frequency/blob/e94769b33ef595f634c27c88ab1348ff586a114a/docs/experiments/RESEARCH_ROUTE_REVIEW_20261015.md)
- 验收元数据及独立复算程序：records/phase24_review_20261015/。
