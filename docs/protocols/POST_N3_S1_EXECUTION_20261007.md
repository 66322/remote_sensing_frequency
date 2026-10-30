# N3五组与S1四组冻结执行协议（2026-10-07）

## 决定与范围
用户已授权按交叉问题规划执行。E3/E4/N5边界原件f60491fc1091eb7d272e081e821d9e6397aa9c82独立复算PASS，问题筛选N3/S1通过、R1不通过。九组是新问题的匹配实验，不是扩大N2窗口或挽救N5配方。主线仍RGB–DSM条件互补与退化/缺失分割，恢复旁支；可行性探索，不承诺论文贡献。

每组从固定N1-2完整selected state开始：SHA256 28bc6f8ca5e1221392598b0a6f2d160e8c633a6a9cf63827067df3e7b81a144b。fresh optimizer，新增8000步、seed42、batch16、无梯度累积，last4及heads训练，原N1配对clean/aug裁剪流、geometry_aug=False。九组总72000新更新，其他增强、损失、学习率与N1原plan一致；不接续N5/N2参数。原CE clean/aug各fusion .5、RGB own .125、DSM own .125，沿原有效标签分母。

Potsdam fit12/Val2=3_11、5_10，native512/stride256，NoBoundary fg5主、Full诊断。4000/8000按clean、DSM全缺失、RGB全缺失均值选checkpoint，早步优先；selected普通32条件，fixed8000原22条件。两年龄另评rgb_U/dsm_U各两tile，沿已完成cross冻结U掩码，仅评价，不选模。无T/H/L追加评价、Test6/independent final/held4读取，新seed或失败配方重训。

## N3：条件区域聚合的匹配五组
stride4晚期128通道特征平均池化到stride16，512窗为32×32 tokens。64个8×8固定种子，每种子初始4×4 tokens；单次归属，种子描述为有效固定网格均值，候选限种子网格3×3邻域。空间代价距离平方/16，RGB附加2×余弦距离，DSM附加4×归一化received高度绝对差。RGB描述来自晚期投影特征压缩32通道后归一化；DSM为received归一化输入最近邻采样。描述与归属detach，无label/遮前输入。both-observed且16×16全部有效才供给/查询，空种子排除，空查询残差0。dense onehot+bmm平均/回送，避免CUDA scatter累加。

每组同样两条无bias128×128投影，额外32768参数；固定相同初始化，残差系数0.1。聚合自身模态内容，另一侧只决定区域归属，不交换donor内容。不声称复现SPFormer或DFormerv2。

| 作业 | RGB自身特征 | DSM自身特征 |
|---|---|---|
| N3-0 | 像素消息 | 像素消息 |
| N3-1 | 固定网格聚合 | 固定网格聚合 |
| N3-2 | 像素消息 | RGB描述区域聚合 |
| N3-3 | DSM高度区域聚合 | 像素消息 |
| N3-4固定候选 | DSM高度区域聚合 | RGB描述区域聚合 |

原N1融合与已知缺失精确回退保持。N3-4 selected S_available超过N3-0与N3-1各≥0.3pp，两tile同号、fixed同号；QR超过N3-2≥0.2pp、QD超过N3-3≥0.2pp，各方向两tile/fixed同号。clean/两种全缺失对0/1底线−0.1pp，primary最差条件×tile对0/1底线−0.2pp。固定候选失败不换单侧候选救门槛，不调种子数/窗口/迭代/预算。

## S1：上下文特征与输出策略四格
无新增参数，均A1：物理受损输入按正确标记清零。B1沿原三尺度特征投影/merge支撑掩码；B0保留计算得到的上下文特征。C1局部缺失输出硬回退；C0保留融合输出。整窗一侧全缺失时，四组均使用原安全特征与输出图；两侧均无效处输出0、预测255。无额外专家推理或置信网络。

| 作业 | 特征策略 | 局部输出 |
|---|---|---|
| S1-0 | B1 | C1 |
| S1-1 | B0 | C1 |
| S1-2 | B1 | C0 |
| S1-3固定候选 | B0 | C0 |

以rgb_U/dsm_U池化mIoU均值比较：S1-3对S1-0≥0.5pp，对两个单因素S1-1/S1-2各≥0.2pp；各比较两tile均值/fixed均值正。clean/两种全缺失对S1-0≥−0.1pp，primary最差条件×tile≥−0.2pp。RGB/DSM分别报告；只有通过全部门槛且两方向对全部控制池化/两tile都正才标bilateral_candidate。报告四格交互，但不另设事后门槛；简单单因素匹配联合时关闭组合贡献。原诊断仅C=0下RGB特征增量，不预设双向有效。

## 队列、记录与停止
按N3-0…4、S1-0…3顺序、GPU索引交替分配，一卡一个worker，每lane FIFO；N3-4与S1-0允许异卡并行，不跨族继承参数。仅GPU0/1两H10080GB。CPU准备6h、每作业完整训练/评价12h正有限超时；技术失败停止后续派发，已有另一worker可完成，不自动重试。terminate后60秒仍在则kill，超时即使返回0也不算COMPLETE。科学门槛在九组完成后统一汇总，不触发额外族。

登记器先查本类目录、原队列、活PID/锁与共享successor lease；已登记只返回既有目录，不重复启动。继承cross代码快照逐SHA核验，再覆盖本协议12文件并生成code_manifest。服务器登记前同包CPU检查，控制器nohup；临时文件、代码、checkpoint、预测、日志、轻量记录全部位于zzx对应research_post_n3_s1_<timestamp>_<pid>。不做重复资源审计。半登记/中断保留记录，人工核对后明确接管，不盲目重训。

预计九组23—34小时粗范围，新区域算子尚无H100实测；首个完整作业后校准，不承诺跑满两天或保证结束。完成N3_S1_COMPLETE_AWAITING_REVIEW后显式轻量上传、GitHub独立复算，再决定去留。CPU合成测试不是真实DINO/GPU性能或科学结果。

## 证据
[诊断验收](../experiments/POST_N5_CROSS_RESULTS_20261007.md)、[原交叉规划](POST_N5_CROSS_QUESTION_48H_PLAN_20261006.md)、[实现验证](../../records/post_n3_s1_execution_design_20261007/validation.json)。固定门槛是事前协议，不从结果后验选最高项。seed42/两Val tile只作开发证据，不称独立泛化或显著性。

