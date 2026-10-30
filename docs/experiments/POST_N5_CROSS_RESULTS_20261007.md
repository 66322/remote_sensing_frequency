# E3/E4与N5边界复查：独立验收（2026-10-07）

实验已验证的范围：Potsdam fit12/Val2=3_11、5_10，native512/stride256，seed42固定模型，NoBoundary fg5主、Full诊断；执行d1ed1a42093c40c979509eac54ba730d89692c1b，新增训练0。最后用户查询2026-10-07T07:38:05.617099+08:00，queue最后观测01:08:32.994625，三个E4 worker COMPLETE，查询时controller/worker均LIVE=False。记录上传f60491fc1091eb7d272e081e821d9e6397aa9c82。

## 原件与复算范围
[上传原件](../../records/research_post_n5_cross_20261006T235526_442218/evidence_20261007T075655372529_677219/manifest.json)：352载荷+manifest共353文件，路径/大小全部匹配Git tree。独立回读238 JSON载荷及manifest，原始解码SHA/上传SHA通过；复算4128矩阵、1168 joint，192 case绑定、576预测索引绑定、106源码索引绑定。独立审计不导入工程模型、训练或数据集，复算整数池化、TP/FP/FN/IoU与分母、固定筛选，PASS。

代码清单中3个继承旧plan JSON仅有manifest SHA索引，不在上传器.py/.md快照载荷中：D30 plan、D27 plan、post-D30 design plan。这不是本次352载荷缺项。没有逐字回读全部非JSON载荷或服务器.npy/.npz/.pth，也未重放GPU；A负控制/C上游首batch一致性和旧E2 parity属于上传元数据一致性核对，未对服务器数组重新求SHA。审计范围见[README](../../records/post_n5_cross_offline_audit_20261007/README.md)及[audit_result.json](../../records/post_n5_cross_offline_audit_20261007/audit_result.json)。

## E4三因素：S1问题通过，R1不通过
固定output对比A1B1C0−A1B1C1的RGB增量：N1-2 −0.299884pp、N2-0 +0.401156pp、N2-3 +0.399911pp，均两tile异号，R1问题门槛False。
固定feature对比A1B0C0−A1B1C0在C=0条件下：

| 模型 | RGB池化增量pp | 3_11 | 5_10 | DSM池化增量pp |
|---|---:|---:|---:|---:|
| N1-2 | 1.307603 | 1.063997 | 1.609402 | 0.002574 |
| N2-0 | 0.577591 | 0.372410 | 0.830775 | −0.026330 |
| N2-3旁证 | 0.595287 | 0.393567 | 0.845260 | −0.033523 |

RGB固定问题门槛通过，DSM未过。这支持训练检验“保留融合时上下文特征能否有用”，不能写为单独移除掩码必定有效或双向方法贡献。原E2门槛不改判；各列原始两tileCM/支持量在原件与审计结果中。

## N5后边界与E3构成
clean Full 4px边界相对内部的anchor正确并集伤害率差：N5-0在3_11/5_10为14.101202/15.040118pp，N5-3为13.985684/14.959127pp；预定支持分母≥100及两tile≥1pp条件均通过。说明边界压力仍存在，不证明区域聚合有效或跨区传播是原因。

E3按NoBoundary fg5类别×Full4px边界构成标准化，10个共同层均≥100，覆盖质量1。RGB缺失U−H标准化masked accuracy差：A0/B1在两tile为1.057457/0.442777pp，N5-0为0.968306/0.398037pp，N5-3为0.953829/0.437904pp。A0/B1在masked像素相同来自原硬回退到相同专家，不能当两独立重复。L规则仍跨tile混合。标准化的是masked accuracy，不是校正mIoU；仍不能隔离为高度纯因果。N5固定混合增量失败保持，构成分析不挽救该配方。

## 决定与交接
N3五组与S1四组按已有用户授权落实，R1跳过；不追加别族填时长。N3测试条件区域归属是否超过局部/网格，S1测试特征×输出四格；九组固定N1-2 state、新8000步/组。新执行[冻结协议](../protocols/POST_N3_S1_EXECUTION_20261007.md)与代码已实现，CPU验证通过，但没有新服务器登记回报。研究阶段仍可行性探索，主线/旁支不变，N2/N5/C/N1旧失败不救预算/seed；N4无更新暴露、R2前提失败保持不激活。

