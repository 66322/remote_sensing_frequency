# 混合退化 C0/C1：逐 tile 风险审计结果

## 证据边界

服务器于 **2026-10-01 10:15:16+08:00** 生成[诊断 JSON](../../records/post_d21_mixed_followup_compact_20260930/tile_risk_diagnostics.json)，随后由用户以提交 `3e17b6a` 推送。脚本报告 `TILE RISK AUDIT PASS`：重新核对 E 组 4/4 完成、开发集未加载 Test6、训练/评价摘要与 checkpoint SHA 记录绑定，并从四份服务器评价摘要复算 6×6 整数矩阵、逐类 IoU、pooled 与逐 tile 差值。**checkpoint 二进制没有重新哈希；四份原始评价摘要及预测仍在服务器**。本地检查的是已推送诊断 JSON，不能表述为本地重新运行了全量原始评价。所有结论是 seed42 开发集探索证据。

以下差值均为 C1 可学习前端+CE 减 C0 双三次+CE 的百分点。Potsdam 使用 Val2 NoBoundary 前景五类；Vaihingen 使用同镶嵌图开发区 FullGT 前景五类。

## 局部错误结构

| 数据集、tile 与条件 | 前景五类 mIoU 差 | 主要计数变化（C1−C0） | clean 边界 F1 差 |
|---|---:|---|---|
| Potsdam `5_10`，×2 未见模糊 | −0.209 pp | Car IoU −0.939 pp；误报 +2,982，正确 −234。LowVegetation 正确 −9,793、误报 +7,199 | 未记录 |
| Vaihingen `20`，×2 clean | −0.815 pp | Car IoU −3.996 pp；误报 +1,454，正确 −58；该 tile Car 真值像素 17,858 | Car −3.354 pp |
| Vaihingen `20`，×2 未见模糊 | −0.287 pp | Car IoU −2.144 pp；误报 +1,231，正确 +133 | 未记录 |
| Vaihingen `33`，×2 未见模糊 | −1.421 pp | LowVegetation 正确 −20,357、漏报 +20,357；Building 正确 −17,359；Tree 误报 +23,905，尽管 Tree 正确 +4,343 | 未记录 |
| Vaihingen `33`，×4 未见模糊 | −0.685 pp | LowVegetation 正确 −11,734；Building 正确 −6,940；Tree 误报 +15,223 | 未记录 |

Vaihingen `33` 的 Tree 与 LowVegetation 在 ×4 clean 也分别下降 −1.789/−0.924 pp；Tree clean 边界 F1 下降 −0.810 pp。各类别的误报/漏报是边际计数，**不能据此断言具体像素从 LowVegetation 被错分到了 Tree**；若要确定流向，需要比较两份完整 6×6 矩阵的非对角元素。未见模糊条件没有边界计数。

四个条件的 pooled 增益仍分别为 Potsdam +0.387/+0.926/+0.424/+0.963 pp、Vaihingen +0.151/+0.425/+0.288/+0.586 pp。Vaihingen 对应下降 tile 数为 6/17、3/17、5/17、5/17，不能以 pooled 正值覆盖局部风险。诊断中指定 tile 的 C1 像素 L1 都高于 C0，但该值来自重叠窗口像素加权的推理诊断，C1 只接受分割 CE 训练，不能把 L1 升高直接解释为分割失败的原因或将其当作论文主指标。

## 决定与下一轮

C1 保留为**开发候选**，当前不能写成跨地区稳定有效的确认性结果。下一轮优先准备独立地理来源的带标签数据，先验收来源、类映射、影像/标签配准、split 隔离、许可、大小、SHA 和服务器可达路径；GitHub/Hugging Face 可直接访问，其他来源先规划 Colab/Hugging Face 中转，不直接排下载或训练队列。独立来源通过验收后，冻结现有 C0/C1 checkpoint、预处理和四个合成条件，在新地区做成对评价，报告 pooled、逐 tile 和 Car/Tree/LowVegetation 计数。若外部类别定义不能严格对应现有六类，只报告可比类别的分项指标，不把它直接并入原 foreground-five mIoU。评价结果只用于一次性外部检验，不在该地区调参。

[UAVid 官方页面](https://uavid.nl/)公开描述了 Building、Road、Tree、Low vegetation、Static/Moving car 等类别，可作为**案头候选**；它是无人机街景视角，Road 不覆盖全部 Impervious，汽车需合并且 Human 需另行处理，因此目前不满足直接套用现有六类指标的条件。其下载入口不是已确认可由服务器直接访问的 GitHub/Hugging Face 资产，许可、大小与中转路线仍需单独核对。GAMUS 也只是候选之一，没有指定其为必选数据集。

若独立来源短期内不可用，可在现有训练数据上设计**容量匹配的可训练前端对照**，与 C1 保持同骨干、输入、参数量量级、训练预算和退化，再执行单 seed42 探索；它回答 C1 收益是否主要来自额外可训练容量。该对照的实现和吞吐须先审计，不能把新的开发集模型调优包装成外部确认。现阶段不补第三种子、不解封 Test6，也不为了凑运行时长重复旧组。
