# D23双卡工程记录：GitHub原件验收通过

来源提交d3829b600177304ae23865e2a15e22aa767e1f3f，实验目录research_d23_b_engine_admission_20261001T140528_658274，执行入口40fca5adf4ded1277de264ffc361b67fbaaca0c8。标签：**代码已实现、实验已验证（工程验收范围）**；不是开发集精度或论文确认性结果。

## 原件回读与复算

[服务器上传的9份文件](../../records/research_d23_b_engine_admission_20261001T140528_658274/evidence_20261001T143256013644_712824/upload_manifest.json)已从GitHub读取。8份原文件共402290字节，全部长度/SHA256与manifest一致；新增manifest为索引。5份实际执行源码及基础配置/split共7份SHA与仓库文件一致。两设备公共签名一致，仅gpu/uuid不同；专家checkpoint SHA和saved_probe_reproduced=true在两卡preflight中一致。

CPU原日志明确22项检查通过、5.480秒。GPU日志明确全部训练与评价条件完成，没有异常终止；xFormers disabled/不可用警告与本轮记录一致。

| 项目 | GPU0 smoke | GPU1 profile |
|---|---|---|
| 最后观测 | 2026-10-01T14:06:05.496624+08:00 | 2026-10-01T14:07:44.235024+08:00 |
| 训练检查 | 8组，每组2步，重载相等 | TSF12步，重载相等 |
| 评价 | 768×768，14条件，6固定+TSF | 6000×6000，3条件，R0/M0_safe/TSF |
| 总耗时 | 28.3567秒 | 98.1620秒 |
| 主机峰值RSS | 3063578624字节 | 10096214016字节 |
| 各组训练最大allocated | 2619051008字节 | 2439812608字节 |
| 最终reserved | 3317694464字节 | 3028287488字节 |

GPU0在每组训练前reset显存计数，因此采用各组训练值最大值，而不是把最终summary的allocated当作全程峰值。GPU1训练步去掉前两步的中位耗时0.18741658秒，只覆盖单tile工程profile。

两卡H10080GB，torch2.2.2+cu121；专家固定micro8，gate16，合并两视图loss单次backward。TF32 matmul/cudnn均true。没有gate梯度累积，专家分块用于固定已有数值执行口径，不代表80GB容量不足。

107条6×6混淆矩阵全部为非负安全整数，逐条复算support/TP/FP/FN、fg5/6类mIoU一致。all=available+missing、逐类总数、rescue-harm=相对R0正确像素净变化一致。所有aux条件R0预测SHA保持clean不变；全部模型缺失区域服务器原摘要记录logits相等，harm/rescue均0；全DSM缺失预测SHA与R0一致。GPU0缺失面积589824/147456/73728（全缺失/四分之一/八分之一条带）；GPU1全缺失36000000、条带4500000。计算审计见[JSON](../../records/research_d23_b_compact_20261001/github_engine_admission_audit.json)。

## 已解决与证据边界

已解决此前GPU0完整身份/时钟/训练接口和CPU原日志缺失；无需重跑本次工程验收。原summary的remaining静态列表仍含“server full-engine admission”，属于生成时预置待办，不作为当前门禁；原件保持不改，current入口标记本项已完成。

smoke评价TSF是重新初始化的g=0.5接口；8组只训练各2步。profile只有训练tile2_12和12步。不能将这些mIoU/损害计数当作TSF优于固定融合、频率独立贡献、Val2性能或泛化证据。formal_fit_statistics和formal_training_started均false。

原始预测.npy、训练状态.pth、admission_fit_statistics及D21 input_manifest原文件不在此次上传清单。预测/权重SHA、重载、input_manifest SHA和缺失logits相等目前是原日志/摘要中的运行报告；助手没有重新执行推理或独立读取这些二进制文件。归档29924字节/SHA e290548c50758e3d228f6e00e4e36bf4592efcf5daf2739994b6a28ee18278fa仍只在服务器，未接收tar原件。

## 下一步与停止条件

只剩正式工程预算准备：12个gate-fit tile缓存及256个TCAP统计样本的I/O、两卡并行资源、每组4000步加Val2×14条件的保守wall/job/磁盘预算；随后按源码/backend绑定生成runtime lock与8组队列。当前FULL_ENGINE_RUNTIME_ADMITTED锁未生成，不能从本次小规模步速直接批准正式运行。

资源测量不读取Test6，不使用Val2精度筛选参数，不改变8组/14条件/NoBoundary fg5与原机制风险阈值。发生绑定漂移、非有限数值、回退失败或预算超限时停止该测量，保留目录诊断；预算达标才进入正式固定4000步screen。研究仍为可行性探索：频率＋语义可靠性优先，C1旁支，不从工程成功更改方向。
