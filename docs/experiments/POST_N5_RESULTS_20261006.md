# N5四组结果验收与去留（2026-10-06）

## Material Passport
- Origin Skill: academic-research-suite / experiment-agent
- Origin Mode: validate
- Verification Status: ANALYZED（原件/绑定/计数及固定gate独立离线复算PASS；未重训或重新GPU推理）
- Version Label: post_n5_results_v1
- 结论角色：Potsdam Val2、seed42开发证据；去留沿原冻结协议，不改变论文主线。

## 完成、来源与实际耗时

用户status回报最后queue观测2026-10-06T21:16:59.632381+08:00，N5_COMPLETE_AWAITING_REVIEW；四组COMPLETE，controller及worker LIVE=False（只读查询时刻未单列）。N5-0/1于16:42:57、N5-2/3于21:16:35/40完成。科学执行提交[2e565cc](https://github.com/66322/remote_sensing_frequency/commit/2e565cca04d84d8605a96105d12fb6c0871e464d)，[冻结协议](../protocols/POST_N5_EXECUTION_20261006.md)。

原件上传[1bd58b6](https://github.com/66322/remote_sensing_frequency/commit/1bd58b6a64e07e8b4ee8d5e87e91f76b8df93898)，[证据目录](../../records/research_post_n5_20261006T114819_71934/evidence_20261006T222506485434_398074)，共871载荷+manifest=872文件，原始1123146691 bytes、上传108601556 bytes，权重/预测/mask本体仍在服务器。目录/home/jovyan/zzx/paper_rebuild/08_thesis_full_repro/records/research_post_n5_20261006T114819_71934。原控制器没有重启或新增失败重训回报。

登记日志11:48:27至queue完成21:16:59约9小时28分；GPU首波11:51:31，四组两波完成约9小时25分，CPU掩码准备约3分钟。第一波约4小时51分、第二波约4小时34分（训练、checkpoint验证与末尾评价合计），不能把纯训练1.31秒/步换算当完整作业耗时。

Potsdam fit12，Val2=3_11、5_10；native512/stride256、NoBoundary fg5主、Full诊断；seed42，新增8000更新/组、batch16无累积。四组均从完整N1-2 state SHA28bc6f8ca5e1221392598b0a6f2d160e8c633a6a9cf63827067df3e7b81a144b出发、重新建立相同optimizer。所有selected=8000。没有Test6、independent final或held4读取；T是Val2上的冻结规则迁移，不是独立地理检验。

## 独立审计范围

- 871载荷路径/大小与未截断Git evidence subtree完全对应；连manifest共872文件，无清单缺项。
- 独立读取50载荷及manifest，上传/无损解码原始SHA通过；另核对固定发布提交的12项N5源码SHA，95项执行文件SHA与原件源索引一致。
- 16份summary：普通selected32/fixed22条件，内容selected/fixed各8条件、两tile。复算124464次矩阵及support/TP/FP/FN/IoU/valid、12304次joint；41472个矩阵池化组、4048个joint池化组一致。
- 560个嵌入case按原写入格式重建后匹配原manifest.source SHA；5040个预测签名与服务器artifact索引匹配。并未逐个下载全部case载荷或重新hash .npy本体。
- 验证八份checkpoint选模记录，三状态池化平均与早选规则正确；四份completion、selected/fixed summary、初始完整state、plan/code/input/config、44个mask的面积/坐标/形状及SHA元数据绑定一致。
- 四组参数128827074、可训练43660786及初始fusion state hash相同。N5-1/2/3的原8槽条件计数与全部loss监督像素数完全相同；新规则/方向次数严格匹配配额。N5-0的原分配监督差异明示，不拿其不同缺失预算证明内容增量。
- 全部固定checks、deltas、scores、direction、retention与reported screen匹配，绝对容差1e-10。

[完整审计结果](../../records/post_n5_offline_audit_20261006/audit_result.json)、[独立CPU脚本](../../scripts/audit_post_n5_received_records.py)、[复算说明](../../records/post_n5_offline_audit_20261006/README.md)。未重新读取服务器权重/原影像/mask/预测本体，不冒称GPU复现或全部871载荷独立解码。

原plan有继承文字漂移：created_at仍10月4日，directory_pattern/automatic_followup/architecture/verification_status及fixed10/selected22文字来自旧族。实际执行提交与worker为N5、原N1模型；普通selected32/fixed22+每tag内容8条件，scope/完成/计数覆盖匹配。它们不意味着旧结构重新启用或漏评价。原科学plan、code与manifest不覆盖修改，当前入口按实际执行证据说明。

## 四组对照结果

全部为NoBoundary fg5百分比或family平均；S_available按C/QR/QD/QJ四family等权，T均值为RGB/DSM两方向pooled fg5平均。

| 组 | 角色 | S_available | clean | DSM全缺失 | RGB全缺失 | T两方向均值 |
|---|---|---:|---:|---:|---:|---:|
| N5-0 | 原条件序列 | 86.687264 | 87.455149 | 86.333744 | 65.759606 | 83.278446 |
| N5-1 | 随机U | 86.365394 | 87.238447 | 86.175120 | 65.771276 | 83.560450 |
| N5-2 | H/L内容 | 86.484846 | 87.339306 | 86.248412 | 65.750434 | 83.655220 |
| N5-3 | 固定U/H/L混合 | 86.392995 | 87.264078 | 86.181473 | 65.764988 | 83.602328 |

同阶段原控制N5-0的S最高；N5-1/2/3相对它分别−0.321870/−0.202418/−0.294270pp。混合组比随机S只+0.027601pp。这些是同stage对比；N5-0新增槽的共同native裁剪与旧N1/N2有区别，不能将其对旧模型的改善全部解释成训练时长或新结构贡献。

局部规则压力有收益：N5-3的T均值相对N5-0+0.323882pp，N5-1相对N5-0+0.282004pp。随机控制已解释大部分局部缺失改善；主要机制比较必须N5-3对N5-1，不能用原分配的不同暴露来替代。

## 固定候选N5-3 gate=False

| 固定比较 | 差值pp | 冻结要求 | 判定 |
|---|---:|---|---|
| T两方向均值，对N5-1 | +0.041878 | ≥+0.5 | 失败 |
| T各tile方向均值 | +0.061222 / +0.025337 | 两tile均正 | 通过 |
| fixed8000 T均值，对N5-1 | +0.041878 | >0 | 通过 |
| clean，对N5-0 | −0.191071 | ≥−0.1 | 失败 |
| DSM全缺失，对N5-0 | −0.152271 | ≥−0.1 | 失败 |
| RGB全缺失，对N5-0 | +0.005382 | ≥−0.1 | 通过 |
| 旧随机缺失8条件均值，对N5-1 | +0.011079 | ≥−0.1 | 通过 |
| primary最差condition×tile，对N5-1 | −0.006953 | ≥−0.2 | 通过 |

T方向分开：
- RGB缺失：pooled+0.013072pp；3_11 −0.016745、5_10 +0.041837pp，tile异号。
- DSM缺失：pooled+0.070685pp；3_11 +0.139189、5_10 +0.008836pp，两tile正但幅度小。

所以passed=False、bilateral_candidate=False。不能把平均两tile正或fixed同号写成足够增量，也不能只报T提升而隐藏clean/全缺失代价。

N5-2的T均值最高，但对随机仅+0.094770pp；它不是事前主候选，不能替换N5-3救gate。其clean相对N5-0也下降0.115842pp。保留全部四组，不追加混合比例、强度、预算或seed搜索。

## 新增暴露与剩余问题

每组128000 crop样本，即8000更新、每更新16个crop且每crop两view；视图总数256000/组，完整和增强fusion有效像素分别33554432000。这里计数单位明确，不能把视图/像素当独立重复。

N5-1/2/3的aug RGB/DSM own有效像素分别29299965952/29293445120完全一致。每方向新增槽：
- N5-1 U32000；
- N5-2 H16000、L16000；
- N5-3 U16000、H8000、L8000。
其余64k样本原条件计数跨三组一致。增强族差异没有额外样本/监督预算优势。

RGB U−H gap：N5-0 0.814705、N5-1 0.871136、N5-2 0.850146、N5-3 0.867095pp。说明高DSM变化位置的局部RGB缺失压力仍存在；不能据此纯因果归于高度变化，类别/边界构成仍未标准化。更强压力本身也不代表简单混合增强能解决。

联合锚点统计亦复算：N5-0/N5-3仅RGB正确保留率约95.425/95.121%，仅DSM正确保留率40.877/40.647%；它们是原固定锚点、primary both-valid支持的描述性比例，不是候选own分支精度。有效像素和非零梯度不能证明N4需要的实际参数更新失衡。

## 去留与下一不确定性

按[原协议](../protocols/POST_N5_EXECUTION_20261006.md)停止当前固定U/H/L混合暴露配方的增量承诺，保留普通适应与随机增强的能力/代价边界。不要重启已完成N5、加seed/预算或选N5-2作为主候选。失败是这套具体分配，不关闭“缺失在哪里”或整个双模态研究问题。

按[扩展规划](../protocols/POST_N2_EXPANDED_PORTFOLIO_20261006.md)先用已有预测完成E3构成诊断及N5-0/N5-3的clean Full边界复查。N3须两者仍满足原边界−内部≥1pp与支持分母条件后再准备五组，重新从固定N1-2开始，匹配局部/网格/两单侧控制；不叠失败N5或挑后验最佳初始化。该边界复查、E3/E4/E5/E6与N3目前尚未执行/登记。

E4拆分输入清零与输出回退可继续独立问题诊断；原E2不因N5失败改判。R1只在E4新问题门槛通过后考虑。N4仍无实际更新暴露证据。R2要求N5/N3各自成立，当前N5失败，本轮组合族不激活。E5形状迁移如执行只限定适用边界，不承担挽救固定gate的作用。

主线RGB–DSM双向条件互补与退化/缺失分割，恢复旁支，阶段可行性探索。当前没有新增训练队列，扩展上限仍21配置，其中N5四项完成，其余为条件储备；未运行不能当负结果或完成项。

## 统计/因果谬误检查：11/11
| 项目 | 处理 |
|---|---|
| Simpson反转 | 方向/tile分别报告，RGB T异号不包装双向一致 |
| 生态推断 | 两tile/seed42不称独立地理泛化 |
| 选择偏差 | Val2持续用于开发；T规则预留不等于final |
| Collider条件化 | 原锚点正确分层只描述保留/伤害，不推因果 |
| 基率忽略 | fusion/own有效像素、新槽规则次数及原条件支持明示 |
| 均值回归 | 固定N5-3、固定N1-2初始化，不挑最高T的N5-2 |
| 幸存者偏差 | 四组全部纳入，无丢掉不利clean/全缺失 |
| 多重搜索 | 不加比例/强度/seed，不以最高分证明方法 |
| 分析自由度 | 原门槛不修改，selected与fixed双口径保留 |
| 相关误写因果 | H困难有构成混杂，局部收益不证明高度因果机制 |
| 反向因果 | mask按输入内容生成，不按标签或模型错误选位置 |

不报告p值/CI或“显著提升”；像素、条件、窗口和双view不是独立训练重复。边界提示、工程完成、开发精度保护和独立泛化分别报告。
